from app.core.llm_parser import parse_response, LLMSignal, _validate_direction, _clamp_float


def test_parse_bullish():
    raw = """```json
{
  "direction": "bullish",
  "confidence": 72,
  "price_target_low": 310.0,
  "price_target_high": 355.0,
  "key_levels": [{"price": 330.0, "rationale": "MA20 support"}],
  "reasoning": "RSI recovering from oversold, MACD bullish cross.",
  "risk_factors": ["Earnings miss", "Market downturn"],
  "technical_score": 68
}
```"""
    signal = parse_response(raw, ticker="0700.HK")
    assert signal.direction == "bullish"
    assert signal.confidence == 72
    assert signal.price_target_low == 310.0
    assert signal.price_target_high == 355.0
    assert len(signal.key_levels) == 1
    assert "RSI" in signal.reasoning
    assert len(signal.risk_factors) == 2
    assert signal.technical_score == 68


def test_parse_bearish():
    raw = '{"direction":"bearish","confidence":65,"price_target_low":250,"price_target_high":280,"key_levels":[],"reasoning":"Testing","risk_factors":[],"technical_score":40}'
    signal = parse_response(raw, ticker="AAPL")
    assert signal.direction == "bearish"
    assert signal.confidence == 65


def test_parse_invalid():
    raw = "This is not JSON at all"
    signal = parse_response(raw, ticker="TEST.HK")
    assert signal.direction == "neutral"
    assert signal.confidence <= 50  # defaults when parsing fails


def test_validate_direction():
    assert _validate_direction("bullish") == "bullish"
    assert _validate_direction("BEARISH") == "bearish"
    assert _validate_direction("random") == "neutral"
    assert _validate_direction("bull market") == "bullish"


def test_parse_complex_fallback():
    """Parser should fallback gracefully on unparseable input."""
    signal = parse_response("This is not JSON at all", ticker="TEST.HK")
    assert signal.direction == "neutral"
