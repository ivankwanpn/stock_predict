from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    ticker: str
    timeframe: str = "short"


class TechnicalSignalResponse(BaseModel):
    ticker: str
    direction: str
    confidence: float
    key_support: float
    key_resistance: float
    indicator_details: dict[str, Any]
    summary: str


class KeyLevel(BaseModel):
    price: float
    type: str  # "support" | "resistance" | "pivot"
    rationale: str
    strength: str  # "weak" | "moderate" | "strong"


class RiskFactor(BaseModel):
    severity: str  # "high" | "medium" | "low"
    factor: str


class Scenario(BaseModel):
    trigger_price: float
    target_price: float
    probability: float  # 0-100
    narrative: str


class LLMSignalResponse(BaseModel):
    ticker: str
    direction: str
    confidence: float
    technical_score: float
    price_target_low: float
    price_target_high: float
    key_levels: list[KeyLevel] = []
    trend_analysis: str = ""
    momentum_analysis: str = ""
    volume_analysis: str = ""
    oscillator_composite: str = ""
    scenario_bullish: Optional[Scenario] = None
    scenario_bearish: Optional[Scenario] = None
    risk_factors: list[RiskFactor] = []
    score_breakdown: Optional[dict] = None
    reasoning: str = ""


class CombinedSignalResponse(BaseModel):
    ticker: str
    technical_direction: str
    technical_confidence: float
    technical_summary: str
    llm_direction: str
    llm_confidence: float
    llm_reasoning: str
    llm_risk_factors: list[RiskFactor] = []
    agreement: str
    combined_confidence: float
    technical_score: float
    price_target_low: float
    price_target_high: float
    key_support: float
    key_resistance: float
    indicator_details: dict[str, Any]


class WatchlistItemResponse(BaseModel):
    ticker: str
    name: str
    latest_price: float
    change_pct: float


class PriceSummaryResponse(BaseModel):
    ticker: str
    company_name: str
    price_summary: dict[str, Any]
    recent_candles: list[dict[str, Any]]


class HistoryResponse(BaseModel):
    ticker: str
    data: list[dict[str, Any]]


class WatchlistAddRequest(BaseModel):
    ticker: str


class WatchlistRemoveRequest(BaseModel):
    ticker: str


class StockSearchResult(BaseModel):
    ticker: str
    name: str
    market: str = "HK"


class IndicatorsResponse(BaseModel):
    ticker: str
    price_summary: dict[str, Any]
    indicators: dict[str, Any]


# ── Chart-data response models ────────────────────────────────────────────────

class TimeValueModel(BaseModel):
    time: str
    value: float


class OHLCVItemModel(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class MovingAverageModel(BaseModel):
    ma5: List[Optional[TimeValueModel]]
    ma10: List[Optional[TimeValueModel]]
    ma20: List[Optional[TimeValueModel]]
    ma60: List[Optional[TimeValueModel]]


class EmaModel(BaseModel):
    ema5: List[Optional[TimeValueModel]]
    ema10: List[Optional[TimeValueModel]]
    ema20: List[Optional[TimeValueModel]]
    ema60: List[Optional[TimeValueModel]]


class BollingerBandModel(BaseModel):
    upper: List[Optional[TimeValueModel]]
    middle: List[Optional[TimeValueModel]]
    lower: List[Optional[TimeValueModel]]


class KeltnerChannelModel(BaseModel):
    upper: List[Optional[TimeValueModel]]
    middle: List[Optional[TimeValueModel]]
    lower: List[Optional[TimeValueModel]]


class IchimokuModel(BaseModel):
    tenkan: List[Optional[TimeValueModel]]
    kijun: List[Optional[TimeValueModel]]
    senkouA: List[Optional[TimeValueModel]]
    senkouB: List[Optional[TimeValueModel]]
    chikou: List[Optional[TimeValueModel]]


class MacdModel(BaseModel):
    macd: List[Optional[TimeValueModel]]
    signal: List[Optional[TimeValueModel]]
    histogram: List[Optional[TimeValueModel]]


class KdjModel(BaseModel):
    k: List[Optional[TimeValueModel]]
    d: List[Optional[TimeValueModel]]
    j: List[Optional[TimeValueModel]]


class ArbrModel(BaseModel):
    ar: List[Optional[TimeValueModel]]
    br: List[Optional[TimeValueModel]]


class DmaModel(BaseModel):
    dma: List[Optional[TimeValueModel]]
    ama: List[Optional[TimeValueModel]]


class IndicatorSetModel(BaseModel):
    ma: MovingAverageModel
    ema: EmaModel
    bb: BollingerBandModel
    sar: List[Optional[TimeValueModel]]
    kc: KeltnerChannelModel
    ichimoku: IchimokuModel
    vwap: List[Optional[TimeValueModel]]
    macd: MacdModel
    kdj: KdjModel
    arbr: ArbrModel
    cr: List[Optional[TimeValueModel]]
    dma: DmaModel
    emv: List[Optional[TimeValueModel]]
    rsi: List[Optional[TimeValueModel]]


class ChartDataResponse(BaseModel):
    ticker: str
    granularity: str
    ohlcv: List[OHLCVItemModel]
    indicators: IndicatorSetModel