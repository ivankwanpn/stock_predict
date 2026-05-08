import type { TimeframeKey } from './timeframeConfig';

// Main chart overlay indicators (only for daily+)
export const OVERLAY_INDICATORS = {
  ma: { labelKey: 'indMA', lines: { ma5: '#FF6B6B', ma10: '#4ECDC4', ma20: '#FFE66D', ma60: '#A78BFA' } },
  ema: { labelKey: 'indEMA', lines: { ema5: '#FF6B6B', ema10: '#4ECDC4', ema20: '#FFE66D', ema60: '#A78BFA' } },
  boll: { labelKey: 'indBOLL', lines: { upper: '#888888', middle: '#AAAAAA', lower: '#888888' } },
  sar: { labelKey: 'indSAR', style: 'dot' as const, color: '#00BCD4' },
  kc: { labelKey: 'indKC', lines: { upper: '#FF9800', middle: '#FFB74D', lower: '#FF9800' } },
  ichimoku: { labelKey: 'indIchimoku', lines: { tenkan: '#2196F3', kijun: '#F44336', senkouA: '#4CAF50', senkouB: '#FF5722', chikou: '#9C27B0' } },
  vwap: { labelKey: 'indVWAP', color: '#FFEB3B' },
} as const;

// Sub-chart indicators
export const SUB_INDICATORS = {
  volume: { labelKey: 'indVolume', type: 'histogram+line' as const, defaultOn: true },
  macd: { labelKey: 'indMACD', type: 'histogram+2lines' as const, defaultOn: false },
  kdj: { labelKey: 'indKDJ', type: '3lines' as const, defaultOn: false },
  arbr: { labelKey: 'indARBR', type: '2lines' as const, defaultOn: false },
  cr: { labelKey: 'indCR', type: '1line' as const, defaultOn: false },
  dma: { labelKey: 'indDMA', type: '2lines' as const, defaultOn: false },
  emv: { labelKey: 'indEMV', type: '1line' as const, defaultOn: false },
  rsi: { labelKey: 'indRSI', type: '1line+2ref' as const, defaultOn: false },
} as const;

export type OverlayKey = keyof typeof OVERLAY_INDICATORS;
export type SubChartKey = keyof typeof SUB_INDICATORS;

export const CHART_THEME = {
  layout: {
    background: { color: '#111827' },
    textColor: '#9CA3AF',
    panes: {
      separatorColor: '#374151',
      separatorHoverColor: '#4B5563',
      enableResize: true,
    },
  },
  grid: {
    vertLines: { color: '#1F2937' },
    horzLines: { color: '#1F2937' },
  },
  crosshair: { mode: 0 },
  rightPriceScale: { borderColor: '#374151' },
  timeScale: {
    borderColor: '#374151',
    timeVisible: true,
    secondsVisible: false,
  },
};

export function getOverlayLineColor(key: OverlayKey, subKey: string): string {
  const cfg = OVERLAY_INDICATORS[key] as any;
  if (key === 'sar') return cfg.color;
  if (key === 'vwap') return cfg.color;
  return cfg.lines[subKey] ?? '#888888';
}

export function isOverlayAvailable(timeframe: TimeframeKey): boolean {
  return timeframe === 'daily' || timeframe === 'weekly' || timeframe === 'monthly' || timeframe === 'quarterly' || timeframe === 'yearly';
}