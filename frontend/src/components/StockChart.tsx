import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from 'lightweight-charts';
import type {
  Time,
  IChartApi,
  ISeriesApi,
  BarData,
  LineData,
  LogicalRange,
  HistogramData,
} from 'lightweight-charts';
import { useLang } from '../i18n/LanguageContext';
import { TIMEFRAMES, getTimeframeConfig, needsResampling, type TimeframeKey } from '../lib/timeframeConfig';
import { resampleOHLCV, resampleIndicatorData, type ResamplePeriod } from '../lib/resample';
import { OVERLAY_INDICATORS, SUB_INDICATORS, CHART_THEME, isOverlayAvailable, type OverlayKey, type SubChartKey } from '../lib/chartUtils';
import type { OHLCVItem, IndicatorSet, TimeValuePoint } from '../types';

interface StockChartProps {
  ticker: string;
  ohlcv: OHLCVItem[];
  indicators: IndicatorSet;
  timeframe: TimeframeKey;
  loading: boolean;
  error: string | null;
  onTimeframeChange?: (tf: TimeframeKey) => void;
}

// --- Data helpers ---

function normalizeTime(timeStr: string, referenceFormat: string): Time {
  if (referenceFormat.includes('T')) {
    return Math.floor(new Date(timeStr).getTime() / 1000) as Time;
  }
  if (timeStr.includes('T')) {
    return timeStr.slice(0, 10) as Time;
  }
  return timeStr as Time;
}

function toLCCandle(item: OHLCVItem, timeRef: string): BarData<Time> {
  return { time: normalizeTime(item.date, timeRef) as Time, open: item.open, high: item.high, low: item.low, close: item.close };
}

function toLCLine(pt: TimeValuePoint | null, timeRef: string): LineData<Time> | null {
  if (!pt || pt.value == null) return null;
  return { time: normalizeTime(pt.time, timeRef) as Time, value: pt.value };
}

function filterNotNull<T>(arr: (T | null)[]): T[] {
  return arr.filter((x): x is T => x !== null);
}

function filterToLatestTradingDay(data: OHLCVItem[]): OHLCVItem[] {
  if (data.length === 0) return data;
  const latestDate = data[data.length - 1].date.slice(0, 10);
  return data.filter(item => item.date.startsWith(latestDate));
}

const SUB_ORDER: SubChartKey[] = ['volume', 'macd', 'kdj', 'rsi', 'arbr', 'cr', 'dma', 'emv'];

function formatTooltipDate(time: Time, tfCfg: ReturnType<typeof getTimeframeConfig>): string {
  if (typeof time === 'string') {
    const d = new Date(time.slice(0, 4) + '-' + time.slice(4, 6) + '-' + time.slice(6, 8));
    if (!isNaN(d.getTime())) return d.toLocaleDateString();
    return time;
  }
  const ts = typeof time === 'number' ? time * 1000 : 0;
  const d = new Date(ts);
  if (isNaN(d.getTime())) return String(time);
  if (tfCfg.granularity === '1h') return d.toLocaleString();
  return d.toLocaleDateString();
}

function formatVolume(v: number): string {
  if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return v.toString();
}

// --- Main component ---

export default function StockChart({ ohlcv, indicators, timeframe, loading, error, onTimeframeChange }: StockChartProps) {
  const { t } = useLang();
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const mainChartRef = useRef<IChartApi | null>(null);
  const mainResizeRef = useRef<ResizeObserver | null>(null);
  const subChartRefs = useRef<Map<SubChartKey, { chart: IChartApi; container: HTMLDivElement; resize: ResizeObserver }>>(new Map());
  const syncingRef = useRef(false);
  const unsubFnsRef = useRef<(() => void)[]>([]);

  // Series refs for crosshair tooltip lookup
  const mainSeriesRef = useRef<{ candlestick?: ISeriesApi<'Candlestick'>; overlays: ISeriesApi<'Line'>[] }>({ overlays: [] });
  const subSeriesRef = useRef<Map<SubChartKey, ISeriesApi<any>[]>>(new Map());
  const tooltipRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const [overlayActive, setOverlayActive] = useState<Set<OverlayKey>>(new Set());
  const [subActive, setSubActive] = useState<Set<SubChartKey>>(new Set(['volume']));

  const tfConfig = getTimeframeConfig(timeframe);
  const showOverlay = isOverlayAvailable(timeframe);

  const processedOHLCV = useMemo(() => {
    let data = ohlcv;
    if (timeframe === 'intraday') {
      data = filterToLatestTradingDay(data);
    } else if (needsResampling(timeframe)) {
      data = resampleOHLCV(data, timeframe as ResamplePeriod);
    }
    return data;
  }, [ohlcv, timeframe]);

  const processedIndicators = useMemo(() => {
    if (!needsResampling(timeframe)) return indicators;
    const result: IndicatorSet = { ...indicators };
    const keys: Array<keyof IndicatorSet> = ['ma', 'ema', 'bb', 'sar', 'kc', 'ichimoku', 'vwap', 'macd', 'kdj', 'arbr', 'cr', 'dma', 'emv', 'rsi'];
    for (const key of keys) {
      const src = indicators[key];
      if (!src) continue;
      if (Array.isArray(src)) {
        (result as any)[key] = resampleIndicatorData(src as TimeValuePoint[], timeframe as ResamplePeriod);
      } else if (src && typeof src === 'object') {
        const resampled: Record<string, TimeValuePoint[]> = {};
        for (const [subKey, arr] of Object.entries(src as Record<string, TimeValuePoint[]>)) {
          resampled[subKey] = resampleIndicatorData(arr, timeframe as ResamplePeriod);
        }
        (result as any)[key] = resampled;
      }
    }
    return result;
  }, [indicators, timeframe]);

  // --- Build main chart (price + overlays) ---

  const buildMainChart = useCallback(() => {
    if (!mainContainerRef.current || processedOHLCV.length === 0) return;
    const container = mainContainerRef.current;

    if (mainChartRef.current) {
      mainChartRef.current.remove();
      mainChartRef.current = null;
    }
    if (mainResizeRef.current) {
      mainResizeRef.current.disconnect();
      mainResizeRef.current = null;
    }

    const oldTooltip = tooltipRefs.current.get('main');
    if (oldTooltip) { oldTooltip.remove(); tooltipRefs.current.delete('main'); }

    const timeRef = processedOHLCV[0].date;
    const candle = (item: OHLCVItem) => toLCCandle(item, timeRef);
    const line = (pt: TimeValuePoint | null) => toLCLine(pt, timeRef);

    const chart = createChart(container, {
      layout: CHART_THEME.layout,
      grid: CHART_THEME.grid,
      crosshair: CHART_THEME.crosshair,
      rightPriceScale: CHART_THEME.rightPriceScale,
      timeScale: { ...CHART_THEME.timeScale, timeVisible: tfConfig.granularity === '1h' },
      autoSize: true,
    });
    mainChartRef.current = chart;

    const tooltip = document.createElement('div');
    tooltip.style.cssText = 'position:fixed;display:none;pointer-events:none;z-index:50;background:#1f2937;border:1px solid #374151;border-radius:0.5rem;padding:0.5rem;font-size:0.75rem;color:#d1d5db;font-family:monospace;min-width:140px;box-shadow:0 10px 15px rgba(0,0,0,0.5);';
    document.body.appendChild(tooltip);
    tooltipRefs.current.set('main', tooltip);

    const overlayRefs: ISeriesApi<'Line'>[] = [];

    if (tfConfig.chartType === 'candlestick') {
      const cs = chart.addSeries(CandlestickSeries, {
        upColor: '#22C55E', downColor: '#EF4444',
        borderUpColor: '#22C55E', borderDownColor: '#EF4444',
        wickUpColor: '#22C55E', wickDownColor: '#EF4444',
      });
      cs.setData(processedOHLCV.map(candle));
      mainSeriesRef.current.candlestick = cs;
    } else {
      const ls = chart.addSeries(LineSeries, { color: '#3B82F6', lineWidth: 2 });
      ls.setData(processedOHLCV.map(item => ({ time: normalizeTime(item.date, timeRef) as Time, value: item.close })));
      mainSeriesRef.current.candlestick = undefined;
    }

    if (showOverlay) {
      for (const key of overlayActive) {
        addOverlaySeries(chart, key, processedIndicators, line, overlayRefs);
      }
    }

    mainSeriesRef.current.overlays = overlayRefs;

    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove(param => {
      if (!param.point) {
        tooltip.style.display = 'none';
        return;
      }
      const rect = container.getBoundingClientRect();
      positionTooltip(tooltip, { x: param.point.x + rect.left, y: param.point.y + rect.top });

      if (!param.time) { tooltip.style.display = 'none'; return; }

      const dateStr = formatTooltipDate(param.time as Time, tfConfig);
      const ohlcvData = processedOHLCV;
      const idx = ohlcvData.findIndex(item => normalizeTime(item.date, timeRef) === param.time);
      if (idx < 0) { tooltip.style.display = 'none'; return; }

      const bar = ohlcvData[idx];
      const prevBar = idx > 0 ? ohlcvData[idx - 1] : null;
      const changePct = prevBar ? ((bar.close - prevBar.close) / prevBar.close * 100).toFixed(2) : null;
      const changeColor = changePct && parseFloat(changePct) >= 0 ? '#22C55E' : '#EF4444';

      let html = `<div style="margin-bottom:0.25rem;color:#9ca3af">${t('tooltipDate')}: ${dateStr}</div>`;
      html += `<div style="display:grid;grid-template-columns:auto auto;gap:0.1rem 0.75rem">`;
      html += `<span style="color:#9ca3af">${t('tooltipOpen')}</span><span>${bar.open.toFixed(2)}</span>`;
      html += `<span style="color:#9ca3af">${t('tooltipHigh')}</span><span>${bar.high.toFixed(2)}</span>`;
      html += `<span style="color:#9ca3af">${t('tooltipLow')}</span><span>${bar.low.toFixed(2)}</span>`;
      html += `<span style="color:#9ca3af">${t('tooltipClose')}</span><span>${bar.close.toFixed(2)}</span>`;
      html += `<span style="color:#9ca3af">${t('tooltipVolume')}</span><span>${formatVolume(bar.volume)}</span>`;
      if (changePct) {
        html += `<span style="color:#9ca3af">${t('tooltipChange')}</span><span style="color:${changeColor}">${parseFloat(changePct) >= 0 ? '+' : ''}${changePct}%</span>`;
      }
      html += `</div>`;

      for (const ov of overlayRefs) {
        const d = param.seriesData.get(ov) as LineData<Time> | undefined;
        if (d && d.value != null) {
          const label = ov.options().title || '';
          html += `<div style="margin-top:0.125rem"><span style="color:#9ca3af">${label}</span> <span>${d.value.toFixed(2)}</span></div>`;
        }
      }

      tooltip.innerHTML = html;
      tooltip.style.display = 'block';
    });

    mainResizeRef.current = new ResizeObserver(entries => {
      const entry = entries[0];
      if (entry && mainChartRef.current) {
        mainChartRef.current.resize(entry.contentRect.width, entry.contentRect.height);
      }
    });
    mainResizeRef.current.observe(container);
  }, [processedOHLCV, processedIndicators, tfConfig, showOverlay, overlayActive, t]);

  // --- Build sub-charts (each in its own container) ---

  const buildSubCharts = useCallback(() => {
    for (const [key, entry] of subChartRefs.current) {
      entry.resize.disconnect();
      entry.chart.remove();
      entry.container.remove();
      const subTip = tooltipRefs.current.get(key);
      if (subTip) { subTip.remove(); tooltipRefs.current.delete(key); }
    }
    subChartRefs.current.clear();
    subSeriesRef.current.clear();

    if (processedOHLCV.length === 0) return;

    const timeRef = processedOHLCV[0].date;
    const line = (pt: TimeValuePoint | null) => toLCLine(pt, timeRef);
    const norm = (t: string) => normalizeTime(t, timeRef);
    const activeSubs = SUB_ORDER.filter(k => subActive.has(k));

    const wrapper = mainContainerRef.current?.parentElement?.parentElement;
    if (!wrapper) return;

    for (const subKey of activeSubs) {
      const card = document.createElement('div');
      card.className = 'bg-gray-900 border border-gray-800 rounded-xl overflow-hidden';

      const header = document.createElement('div');
      header.className = 'px-3 py-1.5 border-b border-gray-800 flex items-center justify-between';
      const label = t(SUB_INDICATORS[subKey].labelKey as any);
      header.innerHTML = `<span class="text-xs font-medium text-gray-300">${label}</span>`;
      card.appendChild(header);

      const chartDiv = document.createElement('div');
      chartDiv.style.minHeight = '120px';
      card.appendChild(chartDiv);

      wrapper.appendChild(card);

      const subChart = createChart(chartDiv, {
        layout: CHART_THEME.layout,
        grid: CHART_THEME.grid,
        crosshair: CHART_THEME.crosshair,
        rightPriceScale: CHART_THEME.rightPriceScale,
        timeScale: { ...CHART_THEME.timeScale, timeVisible: tfConfig.granularity === '1h' },
        autoSize: true,
      });

      const seriesList: ISeriesApi<any>[] = [];
      addSubChartSeries(subChart, subKey, processedOHLCV, processedIndicators, line, norm, seriesList);
      subSeriesRef.current.set(subKey, seriesList);

      const subTooltip = document.createElement('div');
      subTooltip.style.cssText = 'position:fixed;display:none;pointer-events:none;z-index:50;background:#1f2937;border:1px solid #374151;border-radius:0.5rem;padding:0.5rem;font-size:0.75rem;color:#d1d5db;font-family:monospace;min-width:120px;box-shadow:0 10px 15px rgba(0,0,0,0.5);';
      document.body.appendChild(subTooltip);
      tooltipRefs.current.set(subKey, subTooltip);

      subChart.subscribeCrosshairMove(param => {
        if (!param.point) { subTooltip.style.display = 'none'; return; }
        const rect = chartDiv.getBoundingClientRect();
        positionTooltip(subTooltip, { x: param.point.x + rect.left, y: param.point.y + rect.top });

        if (!param.time) { subTooltip.style.display = 'none'; return; }
        const dateStr = formatTooltipDate(param.time as Time, tfConfig);

        let html = `<div style="margin-bottom:0.25rem;color:#9ca3af">${t('tooltipDate')}: ${dateStr}</div>`;
        html += subChartTooltipHTML(subKey, param, seriesList);
        subTooltip.innerHTML = html;
        subTooltip.style.display = 'block';
      });

      subChart.timeScale().fitContent();

      const resize = new ResizeObserver(entries => {
        const entry = entries[0];
        if (entry && subChart) {
          subChart.resize(entry.contentRect.width, entry.contentRect.height);
        }
      });
      resize.observe(chartDiv);

      subChartRefs.current.set(subKey, { chart: subChart, container: card, resize });
    }
  }, [processedOHLCV, processedIndicators, tfConfig, subActive, t]);

  // --- Time scale synchronization ---

  const syncTimeScales = useCallback(() => {
    const handler = (range: LogicalRange | null) => {
      if (syncingRef.current || !range) return;
      syncingRef.current = true;
      const allCharts: IChartApi[] = [];
      if (mainChartRef.current) allCharts.push(mainChartRef.current);
      for (const [, entry] of subChartRefs.current) {
        allCharts.push(entry.chart);
      }
      for (const other of allCharts) {
        try { other.timeScale().setVisibleLogicalRange(range); } catch {}
      }
      syncingRef.current = false;
    };

    const allCharts: IChartApi[] = [];
    if (mainChartRef.current) allCharts.push(mainChartRef.current);
    for (const [, entry] of subChartRefs.current) {
      allCharts.push(entry.chart);
    }
    if (allCharts.length < 2) return;

    for (const chart of allCharts) {
      chart.timeScale().subscribeVisibleLogicalRangeChange(handler);
    }
    unsubFnsRef.current = allCharts.map(chart => () => chart.timeScale().unsubscribeVisibleLogicalRangeChange(handler));
  }, []);

  // --- Lifecycle ---

  useEffect(() => {
    buildMainChart();
    return () => {
      if (mainResizeRef.current) { mainResizeRef.current.disconnect(); mainResizeRef.current = null; }
      if (mainChartRef.current) { mainChartRef.current.remove(); mainChartRef.current = null; }
      const mainTip = tooltipRefs.current.get('main');
      if (mainTip) { mainTip.remove(); tooltipRefs.current.delete('main'); }
    };
  }, [buildMainChart]);

  useEffect(() => {
    buildSubCharts();
    return () => {
      for (const [key, entry] of subChartRefs.current) {
        entry.resize.disconnect();
        entry.chart.remove();
        entry.container.remove();
        const subTip = tooltipRefs.current.get(key);
        if (subTip) { subTip.remove(); tooltipRefs.current.delete(key); }
      }
      subChartRefs.current.clear();
    };
  }, [buildSubCharts]);

  useEffect(() => {
    syncTimeScales();
    return () => {
      for (const fn of unsubFnsRef.current) fn();
      unsubFnsRef.current = [];
    };
  }, [buildMainChart, buildSubCharts]);

  // --- Overlay series helpers ---

  function addOverlaySeries(chart: IChartApi, key: OverlayKey, ind: IndicatorSet, toLine: (pt: TimeValuePoint | null) => LineData<Time> | null, outRefs: ISeriesApi<'Line'>[]) {
    switch (key) {
      case 'ma': {
        for (const [subKey, color] of Object.entries(OVERLAY_INDICATORS.ma.lines)) {
          const data = (ind.ma as any)?.[subKey];
          if (data) {
            const s = chart.addSeries(LineSeries, { color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: subKey.toUpperCase() });
            s.setData(filterNotNull(data.map(toLine)));
            outRefs.push(s);
          }
        }
        break;
      }
      case 'ema': {
        for (const [subKey, color] of Object.entries(OVERLAY_INDICATORS.ema.lines)) {
          const data = (ind.ema as any)?.[subKey];
          if (data) {
            const s = chart.addSeries(LineSeries, { color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: subKey.toUpperCase() });
            s.setData(filterNotNull(data.map(toLine)));
            outRefs.push(s);
          }
        }
        break;
      }
      case 'boll': {
        for (const [subKey, color] of Object.entries(OVERLAY_INDICATORS.boll.lines)) {
          const data = (ind.bb as any)?.[subKey];
          if (data) {
            const s = chart.addSeries(LineSeries, { color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: subKey });
            s.setData(filterNotNull(data.map(toLine)));
            outRefs.push(s);
          }
        }
        break;
      }
      case 'sar': {
        const sar = ind.sar;
        if (sar) {
          const s = chart.addSeries(LineSeries, { color: OVERLAY_INDICATORS.sar.color, lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 2, lastValueVisible: false, priceLineVisible: false, title: 'SAR' });
          s.setData(filterNotNull(sar.map(toLine)));
          outRefs.push(s);
        }
        break;
      }
      case 'kc': {
        for (const [subKey, color] of Object.entries(OVERLAY_INDICATORS.kc.lines)) {
          const data = (ind.kc as any)?.[subKey];
          if (data) {
            const s = chart.addSeries(LineSeries, { color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: subKey });
            s.setData(filterNotNull(data.map(toLine)));
            outRefs.push(s);
          }
        }
        break;
      }
      case 'ichimoku': {
        for (const [subKey, color] of Object.entries(OVERLAY_INDICATORS.ichimoku.lines)) {
          const data = (ind.ichimoku as any)?.[subKey];
          if (data) {
            const s = chart.addSeries(LineSeries, { color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: subKey });
            s.setData(filterNotNull(data.map(toLine)));
            outRefs.push(s);
          }
        }
        break;
      }
      case 'vwap': {
        const vwap = ind.vwap;
        if (vwap) {
          const s = chart.addSeries(LineSeries, { color: OVERLAY_INDICATORS.vwap.color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: 'VWAP' });
          s.setData(filterNotNull(vwap.map(toLine)));
          outRefs.push(s);
        }
        break;
      }
    }
  }

  // --- Tooltip positioning (overflow-safe) ---

function positionTooltip(tooltipEl: HTMLDivElement, point: { x: number; y: number }) {
  const gap = 6;
  const tooltipWidth = tooltipEl.offsetWidth || 160;
  const tooltipHeight = tooltipEl.offsetHeight || 100;

  let x = point.x + gap;
  let y = point.y - tooltipHeight / 2;

  if (x + tooltipWidth > window.innerWidth - gap) {
    x = point.x - tooltipWidth - gap;
  }
  if (y + tooltipHeight > window.innerHeight - gap) {
    y = window.innerHeight - tooltipHeight - gap;
  }
  if (y < gap) {
    y = gap;
  }

  tooltipEl.style.left = `${x}px`;
  tooltipEl.style.top = `${y}px`;
}

// --- Sub-chart series helpers (single chart, no paneIndex) ---

  function addSubChartSeries(chart: IChartApi, key: SubChartKey, ohlcvData: OHLCVItem[], ind: IndicatorSet, toLine: (pt: TimeValuePoint | null) => LineData<Time> | null, norm: (t: string) => Time, seriesList: ISeriesApi<any>[]) {
    switch (key) {
      case 'volume': {
        const hist = chart.addSeries(HistogramSeries, {
          priceFormat: { type: 'volume' },
        });
        hist.setData(ohlcvData.map(item => ({
          time: norm(item.date) as Time,
          value: item.volume,
          color: item.close >= item.open ? 'rgba(34,197,94,0.6)' : 'rgba(239,68,68,0.6)',
        })));
        seriesList.push(hist);
        break;
      }
      case 'macd': {
        const macdData = ind.macd;
        if (!macdData) break;
        const macdLine = (macdData as any)?.macd;
        const signalLine = (macdData as any)?.signal;
        const histData = (macdData as any)?.histogram;
        if (histData) {
          const hist = chart.addSeries(HistogramSeries, { priceFormat: { type: 'price', precision: 3, minMove: 0.001 } });
          hist.setData(filterNotNull(histData.map((pt: TimeValuePoint) => {
            if (pt.value == null) return null;
            return { time: norm(pt.time) as Time, value: pt.value, color: pt.value >= 0 ? 'rgba(34,197,94,0.6)' : 'rgba(239,68,68,0.6)' };
          })));
          seriesList.push(hist);
        }
        if (macdLine) {
          const s = chart.addSeries(LineSeries, { color: '#2962FF', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(macdLine.map(toLine)));
          seriesList.push(s);
        }
        if (signalLine) {
          const s = chart.addSeries(LineSeries, { color: '#FF6D00', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(signalLine.map(toLine)));
          seriesList.push(s);
        }
        break;
      }
      case 'kdj': {
        const kdjData = ind.kdj;
        if (!kdjData) break;
        const kLine = (kdjData as any)?.k;
        const dLine = (kdjData as any)?.d;
        const jLine = (kdjData as any)?.j;
        if (kLine) {
          const s = chart.addSeries(LineSeries, { color: '#2196F3', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(kLine.map(toLine)));
          seriesList.push(s);
        }
        if (dLine) {
          const s = chart.addSeries(LineSeries, { color: '#FF6D00', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(dLine.map(toLine)));
          seriesList.push(s);
        }
        if (jLine) {
          const s = chart.addSeries(LineSeries, { color: '#9C27B0', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(jLine.map(toLine)));
          seriesList.push(s);
        }
        break;
      }
      case 'rsi': {
        const rsiData = ind.rsi;
        if (!rsiData) break;
        const rsiSeries = chart.addSeries(LineSeries, { color: '#7E57C2', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
        rsiSeries.setData(filterNotNull(rsiData.map(toLine)));
        seriesList.push(rsiSeries);
        const rsiValues = filterNotNull(rsiData.map(toLine));
        if (rsiValues.length > 0) {
          const refUp = chart.addSeries(LineSeries, { color: 'rgba(239,83,80,0.5)', lineWidth: 1, lineStyle: 2, lastValueVisible: false, priceLineVisible: false });
          refUp.setData(rsiValues.map(d => ({ time: d.time, value: 70 })));
          seriesList.push(refUp);
          const refDown = chart.addSeries(LineSeries, { color: 'rgba(38,166,154,0.5)', lineWidth: 1, lineStyle: 2, lastValueVisible: false, priceLineVisible: false });
          refDown.setData(rsiValues.map(d => ({ time: d.time, value: 30 })));
          seriesList.push(refDown);
        }
        break;
      }
      case 'arbr': {
        const arbrData = ind.arbr;
        if (!arbrData) break;
        const arLine = (arbrData as any)?.ar;
        const brLine = (arbrData as any)?.br;
        if (arLine) {
          const s = chart.addSeries(LineSeries, { color: '#FF6B6B', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(arLine.map(toLine)));
          seriesList.push(s);
        }
        if (brLine) {
          const s = chart.addSeries(LineSeries, { color: '#4ECDC4', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(brLine.map(toLine)));
          seriesList.push(s);
        }
        break;
      }
      case 'cr': {
        const crData = ind.cr;
        if (!crData) break;
        const s = chart.addSeries(LineSeries, { color: '#FFEB3B', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
        s.setData(filterNotNull(crData.map(toLine)));
        seriesList.push(s);
        break;
      }
      case 'dma': {
        const dmaData = ind.dma;
        if (!dmaData) break;
        const dmaLine = (dmaData as any)?.dma;
        const amaLine = (dmaData as any)?.ama;
        if (dmaLine) {
          const s = chart.addSeries(LineSeries, { color: '#2196F3', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(dmaLine.map(toLine)));
          seriesList.push(s);
        }
        if (amaLine) {
          const s = chart.addSeries(LineSeries, { color: '#FF9800', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
          s.setData(filterNotNull(amaLine.map(toLine)));
          seriesList.push(s);
        }
        break;
      }
      case 'emv': {
        const emvData = ind.emv;
        if (!emvData) break;
        const s = chart.addSeries(LineSeries, { color: '#4ECDC4', lineWidth: 1, lastValueVisible: false, priceLineVisible: false });
        s.setData(filterNotNull(emvData.map(toLine)));
        seriesList.push(s);
        break;
      }
    }
  }

  function subChartTooltipHTML(key: SubChartKey, param: any, seriesList: ISeriesApi<any>[]): string {
    let html = '<div style="display:grid;grid-template-columns:auto auto;gap:0.1rem 0.75rem">';
    switch (key) {
      case 'volume': {
        for (const s of seriesList) {
          const d = param.seriesData.get(s) as HistogramData | undefined;
          if (d && d.value != null) {
            html += `<span style="color:#9ca3af">${t('tooltipVolume')}</span><span>${formatVolume(d.value)}</span>`;
          }
        }
        break;
      }
      case 'macd': {
        const labels = ['MACD', 'Signal'];
        for (let i = 0; i < seriesList.length - 1 && i < 2; i++) {
          const d = param.seriesData.get(seriesList[i]) as LineData<Time> | undefined;
          if (d && d.value != null) {
            html += `<span style="color:#9ca3af">${labels[i]}</span><span>${d.value.toFixed(3)}</span>`;
          }
        }
        if (seriesList.length > 0) {
          const d = param.seriesData.get(seriesList[0]) as HistogramData | undefined;
          if (d && d.value != null) {
            html += `<span style="color:#9ca3af">Hist</span><span style="color:${d.value >= 0 ? '#22C55E' : '#EF4444'}">${d.value.toFixed(3)}</span>`;
          }
        }
        break;
      }
      case 'kdj': {
        const labels = ['K', 'D', 'J'];
        for (let i = 0; i < seriesList.length && i < 3; i++) {
          const d = param.seriesData.get(seriesList[i]) as LineData<Time> | undefined;
          if (d && d.value != null) {
            html += `<span style="color:#9ca3af">${labels[i]}</span><span>${d.value.toFixed(2)}</span>`;
          }
        }
        break;
      }
      case 'rsi': {
        const d = param.seriesData.get(seriesList[0]) as LineData<Time> | undefined;
        if (d && d.value != null) {
          html += `<span style="color:#9ca3af">RSI</span><span>${d.value.toFixed(2)}</span>`;
        }
        break;
      }
      case 'arbr': {
        const labels = ['AR', 'BR'];
        for (let i = 0; i < seriesList.length && i < 2; i++) {
          const d = param.seriesData.get(seriesList[i]) as LineData<Time> | undefined;
          if (d && d.value != null) {
            html += `<span style="color:#9ca3af">${labels[i]}</span><span>${d.value.toFixed(2)}</span>`;
          }
        }
        break;
      }
      case 'cr': {
        const d = param.seriesData.get(seriesList[0]) as LineData<Time> | undefined;
        if (d && d.value != null) {
          html += `<span style="color:#9ca3af">CR</span><span>${d.value.toFixed(2)}</span>`;
        }
        break;
      }
      case 'dma': {
        const labels = ['DMA', 'AMA'];
        for (let i = 0; i < seriesList.length && i < 2; i++) {
          const d = param.seriesData.get(seriesList[i]) as LineData<Time> | undefined;
          if (d && d.value != null) {
            html += `<span style="color:#9ca3af">${labels[i]}</span><span>${d.value.toFixed(2)}</span>`;
          }
        }
        break;
      }
      case 'emv': {
        const d = param.seriesData.get(seriesList[0]) as LineData<Time> | undefined;
        if (d && d.value != null) {
          html += `<span style="color:#9ca3af">EMV</span><span>${d.value.toFixed(2)}</span>`;
        }
        break;
      }
    }
    html += '</div>';
    return html;
  }

  // --- Toggle handlers ---

  function toggleOverlay(key: OverlayKey) {
    setOverlayActive(prev => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  }

  function toggleSub(key: SubChartKey) {
    setSubActive(prev => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  }

  const tfLabelMap: Record<string, string> = {
    intraday: 'tfIntraday', '5day': 'tf5day', daily: 'tfDaily',
    weekly: 'tfWeekly', monthly: 'tfMonthly', quarterly: 'tfQuarterly', yearly: 'tfYearly',
  };

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
        <div className="flex items-center gap-1 flex-wrap">
          {TIMEFRAMES.map(tf => {
            const lbl = t(tfLabelMap[tf.key] as any) || tf.labelZh;
            return (
              <button key={tf.key} onClick={() => onTimeframeChange?.(tf.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${timeframe === tf.key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}`}>
                {lbl}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-2 items-center mt-3">
          {showOverlay ? (
            <>
              <span className="text-xs text-gray-500 font-medium">{t('overlayIndicators')}:</span>
              {(Object.keys(OVERLAY_INDICATORS) as OverlayKey[]).map(key => (
                <button key={key} onClick={() => toggleOverlay(key)}
                  className={`px-2 py-1 text-xs rounded-md border transition-colors ${overlayActive.has(key) ? 'border-blue-500 bg-blue-600/20 text-blue-400' : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'}`}>
                  {t(OVERLAY_INDICATORS[key].labelKey as any)}
                </button>
              ))}
            </>
          ) : (
            <span className="text-xs text-gray-600">{t('overlayIndicators')}: —</span>
          )}
          <span className="text-xs text-gray-500 font-medium ml-2">{t('subIndicators')}:</span>
          {(Object.keys(SUB_INDICATORS) as SubChartKey[]).map(key => (
            <button key={key} onClick={() => toggleSub(key)}
              className={`px-2 py-1 text-xs rounded-md border transition-colors ${subActive.has(key) ? 'border-blue-500 bg-blue-600/20 text-blue-400' : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'}`}>
              {t(SUB_INDICATORS[key].labelKey as any)}
            </button>
          ))}
        </div>
      </div>

      {/* Main price chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="relative" ref={mainContainerRef} style={{ minHeight: 400 }}>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
              <span className="text-sm text-gray-400">{t('loadingChart')}</span>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
              <span className="text-sm text-red-400">{t('chartUnavailable')}</span>
            </div>
          )}
          {!loading && !error && processedOHLCV.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <span className="text-sm text-gray-500">No chart data</span>
            </div>
          )}
        </div>
      </div>

      {/* Sub-charts are rendered dynamically by buildSubCharts via DOM manipulation */}
    </div>
  );
}