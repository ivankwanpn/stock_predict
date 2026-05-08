export type TimeframeKey = 'intraday' | '5day' | 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export interface TimeframeConfig {
  key: TimeframeKey;
  labelZh: string;
  labelEn: string;
  chartType: 'line' | 'candlestick';
  granularity: '1h' | '1d';
  period: string; // start_date offset
  showOverlayIndicators: boolean; // false for intraday/5day, true for daily+
}

export const TIMEFRAMES: TimeframeConfig[] = [
  { key: 'intraday', labelZh: '分時', labelEn: 'Intraday', chartType: 'line', granularity: '1h', period: '5d', showOverlayIndicators: false },
  { key: '5day', labelZh: '5日', labelEn: '5 Day', chartType: 'line', granularity: '1h', period: '5d', showOverlayIndicators: false },
  { key: 'daily', labelZh: '日線', labelEn: 'Daily', chartType: 'candlestick', granularity: '1d', period: '2y', showOverlayIndicators: true },
  { key: 'weekly', labelZh: '周線', labelEn: 'Weekly', chartType: 'candlestick', granularity: '1d', period: '5y', showOverlayIndicators: true },
  { key: 'monthly', labelZh: '月線', labelEn: 'Monthly', chartType: 'candlestick', granularity: '1d', period: '10y', showOverlayIndicators: true },
  { key: 'quarterly', labelZh: '季K', labelEn: 'Quarterly', chartType: 'candlestick', granularity: '1d', period: '10y', showOverlayIndicators: true },
  { key: 'yearly', labelZh: '年K', labelEn: 'Yearly', chartType: 'candlestick', granularity: '1d', period: '20y', showOverlayIndicators: true },
];

export function getTimeframeConfig(key: TimeframeKey): TimeframeConfig {
  return TIMEFRAMES.find(tf => tf.key === key) ?? TIMEFRAMES[2];
}

export function needsResampling(key: TimeframeKey): boolean {
  return key === 'weekly' || key === 'monthly' || key === 'quarterly' || key === 'yearly';
}

export function getPeriodDates(key: TimeframeKey): { startDate: string; endDate: string } {
  const config = getTimeframeConfig(key);
  const end = new Date();
  const start = new Date();

  switch (config.period) {
    case '5d':
      start.setDate(start.getDate() - 5);
      break;
    case '2y':
      start.setFullYear(start.getFullYear() - 2);
      break;
    case '5y':
      start.setFullYear(start.getFullYear() - 5);
      break;
    case '10y':
      start.setFullYear(start.getFullYear() - 10);
      break;
    case '20y':
      start.setFullYear(start.getFullYear() - 20);
      break;
    default:
      start.setDate(start.getDate() - 30);
  }

  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { startDate: fmt(start), endDate: fmt(end) };
}