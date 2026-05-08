from app.core.signals import TechnicalSignal
from app.core.llm_parser import LLMSignal
from app.core.comparison import combine, CombinedSignal, format_comparison


def _make_tech(direction, confidence):
    return TechnicalSignal(
        ticker="TEST.HK", direction=direction, confidence=confidence,
        key_support=100, key_resistance=120, indicator_details={}, summary="test",
    )


def _make_llm(direction, confidence, score=60):
    return LLMSignal(
        ticker="TEST.HK", direction=direction, confidence=confidence,
        price_target_low=100, price_target_high=120, key_levels=[],
        trend_analysis="", momentum_analysis="", volume_analysis="",
        oscillator_composite="", scenario_bullish=None, scenario_bearish=None,
        risk_factors=["Risk 1"], score_breakdown=None,
        reasoning="Test reasoning",
        technical_score=score, raw_response="{}",
    )


def test_agree():
    tech = _make_tech("bullish", 70)
    llm = _make_llm("bullish", 80)
    result = combine(tech, llm)

    assert result.agreement == "agree"
    assert result.combined_confidence > max(tech.confidence, llm.confidence)
    assert result.technical_direction == "bullish"
    assert result.llm_direction == "bullish"


def test_diverge():
    tech = _make_tech("bullish", 70)
    llm = _make_llm("bearish", 60)
    result = combine(tech, llm)

    assert result.agreement == "diverge"
    assert result.combined_confidence < max(tech.confidence, llm.confidence)


def test_partial():
    tech = _make_tech("bullish", 70)
    llm = _make_llm("neutral", 50)
    result = combine(tech, llm)

    assert result.agreement == "partial"


def test_format():
    tech = _make_tech("bullish", 70)
    llm = _make_llm("bullish", 80)
    result = combine(tech, llm)
    output = format_comparison(result, "Test Company")
    assert "Test Company" in output
    assert "AGREED" in output
    assert "BULLISH" in output


def test_price_fallback():
    tech = _make_tech("bullish", 70)
    llm = LLMSignal(
        ticker="TEST.HK", direction="bullish", confidence=80,
        price_target_low=0, price_target_high=0, key_levels=[],
        trend_analysis="", momentum_analysis="", volume_analysis="",
        oscillator_composite="", scenario_bullish=None, scenario_bearish=None,
        risk_factors=[], score_breakdown=None,
        reasoning="test",
        technical_score=60, raw_response="{}",
    )
    result = combine(tech, llm)
    assert result.price_target_low == tech.key_support
    assert result.price_target_high == tech.key_resistance
