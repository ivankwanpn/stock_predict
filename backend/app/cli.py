from __future__ import annotations

import argparse
import sys

from app.core.comparison import CombinedSignal, format_comparison
from app.services.comparison_service import combine_signals


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Run dual-track (technical + LLM) stock analysis.",
    )
    parser.add_argument(
        "ticker",
        help="Stock ticker symbol (e.g., 0700.HK)",
    )
    parser.add_argument(
        "--timeframe",
        choices=["short", "mid", "long"],
        default="short",
        help="Analysis timeframe (default: short)",
    )
    args = parser.parse_args()

    try:
        response = combine_signals(args.ticker, timeframe=args.timeframe)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Unexpected error during analysis: {e}", file=sys.stderr)
        return 1

    # Check for analysis-level errors embedded in the response
    has_tech_error = "error" in response.technical_summary.lower()
    has_llm_error = "error" in response.llm_reasoning.lower()
    if has_tech_error or has_llm_error:
        errors = []
        if has_tech_error:
            errors.append(f"Technical: {response.technical_summary}")
        if has_llm_error:
            errors.append(f"LLM: {response.llm_reasoning}")
        print("Error: Analysis failed for ticker '{}'.\n{}".format(
            args.ticker, "\n".join(errors),
        ), file=sys.stderr)
        return 1

    # Convert risk factor dicts/objects to strings for format_comparison
    safe_risk_factors: list[str] = []
    for rf in response.llm_risk_factors:
        if isinstance(rf, str):
            safe_risk_factors.append(rf)
        elif isinstance(rf, dict):
            severity = rf.get("severity", "?").upper()
            factor = rf.get("factor", rf.get("description", str(rf)))
            safe_risk_factors.append(f"[{severity}] {factor}")
        else:
            safe_risk_factors.append(str(rf))

    combined = CombinedSignal(
        ticker=response.ticker,
        technical_direction=response.technical_direction,
        technical_confidence=response.technical_confidence,
        technical_summary=response.technical_summary,
        llm_direction=response.llm_direction,
        llm_confidence=response.llm_confidence,
        llm_reasoning=response.llm_reasoning,
        llm_risk_factors=safe_risk_factors,
        agreement=response.agreement,
        combined_confidence=response.combined_confidence,
        technical_score=response.technical_score,
        price_target_low=response.price_target_low,
        price_target_high=response.price_target_high,
        key_support=response.key_support,
        key_resistance=response.key_resistance,
    )

    output = format_comparison(combined)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
