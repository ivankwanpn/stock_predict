import logging

from app.core.llm_client import analyze as llm_analyze
from app.core.llm_prompts import SYSTEM_PROMPT, build_analysis_prompt
from app.core.llm_parser import parse_response
from app.models.schemas import LLMSignalResponse, KeyLevel, RiskFactor, Scenario
from app.services.data_service import fetch_ohlcv, get_company_name
from app.core.indicators import compute_all_indicators

logger = logging.getLogger(__name__)


def _safe_key_levels(raw_levels: list) -> list[KeyLevel]:
    result = []
    for item in raw_levels:
        if not isinstance(item, dict):
            continue
        try:
            result.append(KeyLevel(
                price=float(item.get("price", 0)),
                type=str(item.get("type", "")),
                rationale=str(item.get("rationale", "")),
                strength=str(item.get("strength", "moderate")),
            ))
        except (ValueError, TypeError):
            logger.warning("Skipping malformed key_level: %s", item)
    return result


def _safe_risk_factors(raw_factors: list) -> list[RiskFactor]:
    result = []
    for item in raw_factors:
        if isinstance(item, str):
            result.append(RiskFactor(severity="medium", factor=item))
            continue
        if not isinstance(item, dict):
            continue
        result.append(RiskFactor(
            severity=str(item.get("severity", "medium")),
            factor=str(item.get("factor", "")),
        ))
    return result


def _safe_scenario(raw: dict | None) -> Scenario | None:
    if not isinstance(raw, dict):
        return None
    try:
        return Scenario(
            trigger_price=float(raw.get("trigger_price", 0)),
            target_price=float(raw.get("target_price", 0)),
            probability=float(raw.get("probability", 0)),
            narrative=str(raw.get("narrative", "")),
        )
    except (ValueError, TypeError):
        logger.warning("Skipping malformed scenario: %s", raw)
        return None


def analyze_ticker(ticker: str, timeframe: str = "short") -> LLMSignalResponse:
    period_map = {
        "short": "6mo",
        "mid": "1y",
        "long": "2y",
    }
    period = period_map.get(timeframe, "6mo")

    df = fetch_ohlcv(ticker, period=period)
    df_with_indicators = compute_all_indicators(df)
    company_name = get_company_name(ticker)

    prompt = build_analysis_prompt(df_with_indicators, ticker, timeframe, company_name)
    raw_response = llm_analyze(SYSTEM_PROMPT, prompt)
    parsed = parse_response(raw_response, ticker=ticker)

    return LLMSignalResponse(
        ticker=parsed.ticker,
        direction=parsed.direction,
        confidence=parsed.confidence,
        price_target_low=parsed.price_target_low,
        price_target_high=parsed.price_target_high,
        key_levels=_safe_key_levels(parsed.key_levels),
        trend_analysis=parsed.trend_analysis,
        momentum_analysis=parsed.momentum_analysis,
        volume_analysis=parsed.volume_analysis,
        oscillator_composite=parsed.oscillator_composite,
        scenario_bullish=_safe_scenario(parsed.scenario_bullish),
        scenario_bearish=_safe_scenario(parsed.scenario_bearish),
        risk_factors=_safe_risk_factors(parsed.risk_factors),
        score_breakdown=parsed.score_breakdown,
        reasoning=parsed.reasoning,
        technical_score=parsed.technical_score,
    )
