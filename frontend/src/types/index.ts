export interface TechnicalSignal {
  ticker: string;
  direction: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  key_support: number;
  key_resistance: number;
  indicator_details: Record<string, unknown>;
  summary: string;
}

export interface KeyLevel {
  price: number;
  type: 'support' | 'resistance' | 'pivot';
  rationale: string;
  strength: 'weak' | 'moderate' | 'strong';
}

export interface RiskFactor {
  severity: 'high' | 'medium' | 'low';
  factor: string;
}

export interface Scenario {
  trigger_price: number;
  target_price: number;
  probability: number;
  narrative: string;
}

export interface ScoreBreakdown {
  trend: number;
  momentum: number;
  volume: number;
  oscillators: number;
  ichimoku: number;
  sar: number;
}

export interface LLMSignal {
  ticker: string;
  direction: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  price_target_low: number;
  price_target_high: number;
  key_levels: KeyLevel[];
  trend_analysis: string;
  momentum_analysis: string;
  volume_analysis: string;
  oscillator_composite: string;
  scenario_bullish: Scenario | null;
  scenario_bearish: Scenario | null;
  risk_factors: RiskFactor[];
  score_breakdown: ScoreBreakdown | null;
  reasoning: string;
  technical_score: number;
}

export interface CombinedSignal extends TechnicalSignal {
  technical_direction: string;
  llm_direction: string;
  llm_confidence: number;
  llm_reasoning: string;
  llm_risk_factors: RiskFactor[];
  agreement: 'agree' | 'diverge' | 'partial';
  combined_confidence: number;
  price_target_low: number;
  price_target_high: number;
  technical_score: number;
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  latest_price: number;
  change_pct: number;
}

export interface StockSearchResult {
  ticker: string;
  name: string;
  market: string;
}

export interface OHLCVItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TimeValuePoint {
  time: string;
  value: number | null;
}

export interface IndicatorSet {
  ma: Record<string, TimeValuePoint[]>;
  ema: Record<string, TimeValuePoint[]>;
  bb: Record<string, TimeValuePoint[]>;
  sar: TimeValuePoint[];
  kc: Record<string, TimeValuePoint[]>;
  ichimoku: Record<string, TimeValuePoint[]>;
  vwap: TimeValuePoint[];
  macd: Record<string, TimeValuePoint[]>;
  kdj: Record<string, TimeValuePoint[]>;
  arbr: Record<string, TimeValuePoint[]>;
  cr: TimeValuePoint[];
  dma: Record<string, TimeValuePoint[]>;
  emv: TimeValuePoint[];
  rsi: TimeValuePoint[];
}

export interface ChartDataResponse {
  ticker: string;
  granularity: string;
  ohlcv: OHLCVItem[];
  indicators: IndicatorSet;
}


