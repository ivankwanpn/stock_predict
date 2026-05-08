import type { OHLCVItem } from '../types';

export type ResamplePeriod = 'weekly' | 'monthly' | 'quarterly' | 'yearly';

function normalizeDateStr(dateStr: string): string {
  return dateStr.includes('T') ? dateStr.slice(0, 10) : dateStr;
}

function getMondayOfWeek(dateStr: string): string {
  const d = new Date(normalizeDateStr(dateStr));
  const day = d.getUTCDay();
  const diff = d.getUTCDate() - day + (day === 0 ? -6 : 1);
  d.setUTCDate(diff);
  return d.toISOString().slice(0, 10);
}

function getYearMonth(dateStr: string): string {
  return normalizeDateStr(dateStr).slice(0, 7);
}

function getQuarter(dateStr: string): string {
  const norm = normalizeDateStr(dateStr);
  const month = parseInt(norm.slice(5, 7), 10);
  const q = Math.ceil(month / 3);
  return `${norm.slice(0, 4)}-Q${q}`;
}

function getYear(dateStr: string): string {
  return normalizeDateStr(dateStr).slice(0, 4);
}

function groupBy(items: OHLCVItem[], getKey: (d: OHLCVItem) => string): Map<string, OHLCVItem[]> {
  const map = new Map<string, OHLCVItem[]>();
  for (const item of items) {
    const key = getKey(item);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(item);
  }
  return map;
}

function aggregate(items: OHLCVItem[]): OHLCVItem {
  return {
    date: normalizeDateStr(items[items.length - 1].date),
    open: items[0].open,
    high: Math.max(...items.map(i => i.high)),
    low: Math.min(...items.map(i => i.low)),
    close: items[items.length - 1].close,
    volume: items.reduce((s, i) => s + i.volume, 0),
  };
}

export function resampleOHLCV(data: OHLCVItem[], period: ResamplePeriod): OHLCVItem[] {
  if (data.length === 0) return [];
  if (period === 'weekly') {
    const groups = groupBy(data, d => getMondayOfWeek(d.date));
    const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return sorted.map(([_key, items]) => aggregate(items));
  }
  if (period === 'monthly') {
    const groups = groupBy(data, d => getYearMonth(d.date));
    const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return sorted.map(([_key, items]) => aggregate(items));
  }
  if (period === 'quarterly') {
    const groups = groupBy(data, d => getQuarter(d.date));
    const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return sorted.map(([_key, items]) => aggregate(items));
  }
  if (period === 'yearly') {
    const groups = groupBy(data, d => getYear(d.date));
    const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return sorted.map(([_key, items]) => aggregate(items));
  }
  return data;
}

export function resampleIndicatorData(
  data: Array<{ time: string; value: number | null } | null>,
  period: ResamplePeriod
): Array<{ time: string; value: number | null }> {
  if (data.length === 0) return [];
  const filtered = data.filter((d): d is { time: string; value: number | null } => d !== null);
  if (filtered.length === 0) return [];
  const ohlcv: OHLCVItem[] = filtered.map(d => ({ date: d.time, open: 0, high: 0, low: 0, close: d.value ?? 0, volume: 0 }));
  const resampled = resampleOHLCV(ohlcv, period);
  return resampled.map(item => ({ time: item.date, value: item.close }));
}