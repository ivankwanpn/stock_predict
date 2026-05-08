from concurrent.futures import ThreadPoolExecutor

from app.core.signals import TechnicalSignal
from app.core.llm_parser import LLMSignal
from app.core.comparison import combine
from app.models.schemas import CombinedSignalResponse, TechnicalSignalResponse, LLMSignalResponse
from app.services.technical_service import analyze_ticker as technical_analyze
from app.services.llm_service import analyze_ticker as llm_analyze


def combine_signals(
    ticker: str,
    timeframe: str = "short",
) -> CombinedSignalResponse:
    # Run technical and LLM analysis in parallel to reduce total wait time
    with ThreadPoolExecutor(max_workers=2) as executor:
        tech_future = executor.submit(_safe_technical, ticker, timeframe)
        llm_future = executor.submit(_safe_llm, ticker, timeframe)
        tech_response = tech_future.result()
        llm_response = llm_future.result()

    tech_signal = TechnicalSignal(
        ticker=tech_response.ticker,
        direction=tech_response.direction,
        confidence=tech_response.confidence,
        key_support=tech_response.key_support,
        key_resistance=tech_response.key_resistance,
        indicator_details=tech_response.indicator_details,
        summary=tech_response.summary,
    )
    llm_signal = LLMSignal(
        ticker=llm_response.ticker,
        direction=llm_response.direction,
        confidence=llm_response.confidence,
        price_target_low=llm_response.price_target_low,
        price_target_high=llm_response.price_target_high,
        key_levels=llm_response.key_levels,
        trend_analysis=getattr(llm_response, 'trend_analysis', '') or '',
        momentum_analysis=getattr(llm_response, 'momentum_analysis', '') or '',
        volume_analysis=getattr(llm_response, 'volume_analysis', '') or '',
        oscillator_composite=getattr(llm_response, 'oscillator_composite', '') or '',
        scenario_bullish=getattr(llm_response, 'scenario_bullish', None),
        scenario_bearish=getattr(llm_response, 'scenario_bearish', None),
        score_breakdown=getattr(llm_response, 'score_breakdown', None),
        reasoning=llm_response.reasoning,
        risk_factors=llm_response.risk_factors,
        technical_score=llm_response.technical_score,
        raw_response="",
    )

    combined = combine(tech_signal, llm_signal)

    return CombinedSignalResponse(
        ticker=combined.ticker,
        technical_direction=combined.technical_direction,
        technical_confidence=combined.technical_confidence,
        technical_summary=combined.technical_summary,
        llm_direction=combined.llm_direction,
        llm_confidence=combined.llm_confidence,
        llm_reasoning=combined.llm_reasoning,
        llm_risk_factors=combined.llm_risk_factors,
        agreement=combined.agreement,
        combined_confidence=combined.combined_confidence,
        technical_score=combined.technical_score,
        price_target_low=combined.price_target_low,
        price_target_high=combined.price_target_high,
        key_support=combined.key_support,
        key_resistance=combined.key_resistance,
        indicator_details=tech_response.indicator_details,
    )


def _safe_technical(ticker: str, timeframe: str) -> TechnicalSignalResponse:
    try:
        return technical_analyze(ticker, timeframe)
    except Exception as e:
        return TechnicalSignalResponse(
            ticker=ticker, direction="neutral", confidence=0,
            key_support=0.0, key_resistance=0.0, indicator_details={},
            summary=f"Technical analysis error: {e}",
        )


def _safe_llm(ticker: str, timeframe: str) -> LLMSignalResponse:
    try:
        return llm_analyze(ticker, timeframe)
    except Exception as e:
        return LLMSignalResponse(
            ticker=ticker, direction="neutral", confidence=0,
            price_target_low=0.0, price_target_high=0.0, key_levels=[],
            trend_analysis="", momentum_analysis="", volume_analysis="",
            oscillator_composite="", scenario_bullish=None, scenario_bearish=None,
            score_breakdown=None,
            reasoning=f"LLM error: {e}", risk_factors=[], technical_score=0,
        )
