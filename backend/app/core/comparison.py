from dataclasses import dataclass
from app.core.signals import TechnicalSignal
from app.core.llm_parser import LLMSignal


@dataclass
class CombinedSignal:
    ticker: str
    technical_direction: str
    technical_confidence: float
    technical_summary: str
    llm_direction: str
    llm_confidence: float
    llm_reasoning: str
    llm_risk_factors: list
    agreement: str           # "agree" | "diverge" | "partial"
    combined_confidence: float
    technical_score: float
    price_target_low: float
    price_target_high: float
    key_support: float
    key_resistance: float


def combine(tech: TechnicalSignal, llm: LLMSignal) -> CombinedSignal:
    agreement = _compute_agreement(tech.direction, llm.direction)
    combined_conf = _combined_confidence(tech, llm, agreement)

    price_low = llm.price_target_low if llm.price_target_low > 0 else tech.key_support
    price_high = llm.price_target_high if llm.price_target_high > 0 else tech.key_resistance

    return CombinedSignal(
        ticker=tech.ticker or llm.ticker,
        technical_direction=tech.direction,
        technical_confidence=tech.confidence,
        technical_summary=tech.summary,
        llm_direction=llm.direction,
        llm_confidence=llm.confidence,
        llm_reasoning=llm.reasoning,
        llm_risk_factors=llm.risk_factors,
        agreement=agreement,
        combined_confidence=round(combined_conf, 1),
        technical_score=llm.technical_score,
        price_target_low=round(price_low, 2),
        price_target_high=round(price_high, 2),
        key_support=tech.key_support,
        key_resistance=tech.key_resistance,
    )


def format_comparison(result: CombinedSignal, company_name: str = "") -> str:
    name = company_name or result.ticker
    lines = [
        "=" * 60,
        f"  Dual-Track Analysis: {name} ({result.ticker})",
        "=" * 60,
        "",
    ]

    dir_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}

    lines.append(f"  Technical Track  │  {dir_icon.get(result.technical_direction, '⚪')} "
                  f"{result.technical_direction.upper()} ({result.technical_confidence:.0f}%)")
    lines.append(f"  LLM Track         │  {dir_icon.get(result.llm_direction, '⚪')} "
                  f"{result.llm_direction.upper()} ({result.llm_confidence:.0f}%)")
    lines.append("")

    if result.agreement == "agree":
        lines.append(f"  Consensus: ✓ AGREED — Combined Confidence: {result.combined_confidence:.0f}%")
    elif result.agreement == "diverge":
        lines.append(f"  Consensus: ✗ DIVERGED — Tracks disagree. Review both analyses carefully.")
    else:
        lines.append(f"  Consensus: ~ PARTIAL — One track is neutral")

    lines.append("")
    lines.append(f"  Key Support: {result.key_support}  |  Key Resistance: {result.key_resistance}")
    lines.append(f"  Price Target: {result.price_target_low} ~ {result.price_target_high}")
    lines.append("")

    if result.llm_reasoning:
        lines.append(f"  LLM Reasoning: {result.llm_reasoning}")
        lines.append("")

    if result.llm_risk_factors:
        lines.append(f"  Risk Factors: {', '.join(result.llm_risk_factors)}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def _compute_agreement(tech_dir: str, llm_dir: str) -> str:
    if tech_dir == llm_dir:
        return "agree"
    if tech_dir == "neutral" or llm_dir == "neutral":
        return "partial"
    return "diverge"


def _combined_confidence(tech: TechnicalSignal, llm: LLMSignal, agreement: str) -> float:
    if agreement == "agree":
        return min(max(tech.confidence, llm.confidence) * 1.2, 100.0)
    elif agreement == "diverge":
        return (tech.confidence + llm.confidence) / 2 * 0.6
    else:
        return max(tech.confidence, llm.confidence)
