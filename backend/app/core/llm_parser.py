import json
import logging
import math
import re
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class LLMSignal:
    ticker: str
    direction: str          # "bullish" | "bearish" | "neutral"
    confidence: float       # 0.0 - 100.0
    price_target_low: float
    price_target_high: float
    key_levels: list
    trend_analysis: str
    momentum_analysis: str
    volume_analysis: str
    oscillator_composite: str
    scenario_bullish: dict | None
    scenario_bearish: dict | None
    risk_factors: list
    score_breakdown: dict | None
    reasoning: str
    technical_score: float  # 0.0 - 100.0
    raw_response: str

    def dict(self):
        return asdict(self)


def parse_response(raw_text: str, ticker: str = "") -> LLMSignal:
    data = _extract_and_parse(raw_text)

    if data is None:
        logger.warning("Failed to parse LLM response for ticker %s, using fallback", ticker)
        return _fallback(ticker, "Failed to parse LLM response", raw_text)

    return _build_signal(ticker, data, raw_text)


def _extract_and_parse(raw_text: str) -> dict | None:
    text = raw_text.strip()

    # Strategy 1: Try code fence extraction + parse
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        data = _try_parse(fence_match.group(1).strip())
        if data is not None:
            return data

    # Strategy 2: Try bracket-matching extraction
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    data = _try_parse(text[start : i + 1])
                    if data is not None:
                        return data
                    break

    # Strategy 3: Try parsing the whole text directly
    data = _try_parse(text)
    if data is not None:
        return data

    # Strategy 4: Sanitize and retry — fix common LLM JSON issues
    sanitized = _sanitize_json(text)
    data = _try_parse(sanitized)
    if data is not None:
        return data

    return None


def _try_parse(json_str: str) -> dict | None:
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    # Try with ast.literal_eval for Python-style dicts
    try:
        # Replace JS-style values
        fixed = re.sub(r':\s*true\b', ': True', json_str)
        fixed = re.sub(r':\s*false\b', ': False', fixed)
        fixed = re.sub(r':\s*null\b', ': None', fixed)
        import ast
        return ast.literal_eval(fixed)
    except Exception:
        pass
    return None


def _sanitize_json(text: str) -> str:
    """Fix common LLM JSON output issues."""
    # Extract JSON-like region
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    text = text[start:end + 1]

    # Remove control characters (except whitespace)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Fix trailing commas before } or ]
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # Fix unescaped backslashes in strings (common LLM issue)
    # Replace single backslashes that aren't part of escape sequences
    # This is tricky — skip for now

    return text


def _build_signal(ticker: str, data: dict, raw_text: str) -> LLMSignal:
    return LLMSignal(
        ticker=ticker,
        direction=_validate_direction(data.get("direction", "neutral")),
        confidence=_clamp_float(data.get("confidence", 50), 0, 100),
        price_target_low=_clamp_float(data.get("price_target_low", 0), 0, 1_000_000),
        price_target_high=_clamp_float(data.get("price_target_high", 0), 0, 1_000_000),
        key_levels=data.get("key_levels", []),
        trend_analysis=str(data.get("trend_analysis", "")),
        momentum_analysis=str(data.get("momentum_analysis", "")),
        volume_analysis=str(data.get("volume_analysis", "")),
        oscillator_composite=str(data.get("oscillator_composite", "")),
        scenario_bullish=_parse_optional_dict(data.get("scenario_bullish")),
        scenario_bearish=_parse_optional_dict(data.get("scenario_bearish")),
        risk_factors=data.get("risk_factors", []),
        score_breakdown=_parse_optional_dict(data.get("score_breakdown")),
        reasoning=str(data.get("reasoning", "")),
        technical_score=_clamp_float(data.get("technical_score", 50), 0, 100),
        raw_response=raw_text,
    )


def _fallback(ticker: str, reason: str, raw_text: str) -> LLMSignal:
    return LLMSignal(
        ticker=ticker, direction="neutral", confidence=0,
        price_target_low=0, price_target_high=0, key_levels=[],
        trend_analysis="", momentum_analysis="", volume_analysis="",
        oscillator_composite="", scenario_bullish=None, scenario_bearish=None,
        risk_factors=[], score_breakdown=None,
        reasoning=reason, technical_score=0, raw_response=raw_text,
    )


def _parse_optional_dict(val):
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    return None


def _validate_direction(d: str) -> str:
    d = str(d).lower().strip()
    if d in ("bullish", "bearish", "neutral"):
        return d
    if d.startswith("bull") or "bullish" in d:
        return "bullish"
    if d.startswith("bear") or "bearish" in d:
        return "bearish"
    return "neutral"


def _clamp_float(val, lo, hi):
    try:
        return max(lo, min(hi, float(val)))
    except (ValueError, TypeError):
        return lo
