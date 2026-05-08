import json

from app.config import settings
from app.core.indicators import get_indicators_with_descriptions, get_price_summary


SYSTEM_PROMPT = """You are a senior quantitative analyst at a top-tier hedge fund with 20 years of experience in technical analysis. Your task is to produce a comprehensive, detailed analysis of stock data. You must be thorough, specific, and quantitative.

You will receive extensive technical indicator data. You must respond with structured JSON containing:

## Core Signal
1. **direction**: "bullish" | "bearish" | "neutral"
2. **confidence**: 0-100 score based on indicator consensus
3. **technical_score**: 0-100 composite technical score

## Price Targets & Levels
4. **price_target_low**: estimated support / downside target
5. **price_target_high**: estimated resistance / upside target
6. **key_levels**: array of 4-6 critical price levels, each with: price, type (support|resistance|pivot), rationale, strength (weak|moderate|strong)

## Multi-Dimensional Analysis (DETAILED — this is the most important part)
7. **trend_analysis**: Detailed assessment covering:
   - Primary trend direction and strength
   - MA/EMA alignment analysis
   - Ichimoku cloud position interpretation
   - ADX trend strength with specific value
   - SAR signal confirmation
   At least 3-4 sentences.

8. **momentum_analysis**: Detailed assessment covering:
   - RSI position and implication
   - MACD cross/histogram interpretation
   - Stochastic KD signal
   - CCI and Williams %R confirmation
   At least 3-4 sentences.

9. **volume_analysis**: Detailed assessment covering:
   - OBV trend and divergence
   - EMV reading interpretation
   - VWAP position (above/below = buying/selling pressure)
   - Volume relative to 20-day average
   At least 2-3 sentences.

10. **oscillator_composite**: Interpretation of the oscillator composite score (0-100):
    - What the composite value means holistically
    - Whether oscillators confirm or contradict the trend signals
    - Specific levels to watch for reversal

11. **scenario_bullish**: Detailed bullish scenario with:
    - trigger_price: price level that would confirm this scenario
    - target_price: expected upside target
    - probability: 0-100 estimated probability
    - narrative: 2-3 sentence description of what would need to happen

12. **scenario_bearish**: Detailed bearish scenario with:
    - trigger_price: price level that would confirm this scenario
    - target_price: expected downside target
    - probability: 0-100 estimated probability
    - narrative: 2-3 sentence description of what would need to happen

13. **risk_factors**: array of 4-5 specific risks with severity (high|medium|low) and description
    Example: {"severity": "high", "factor": "ADX below 20 indicates weak trend — signals unreliable"}

14. **score_breakdown**: object showing how each category contributes to technical_score:
    {"trend": 25, "momentum": 20, "volume": 15, "oscillators": 15, "ichimoku": 15, "sar": 10}

15. **reasoning**: Executive summary (4-6 detailed paragraphs) synthesizing ALL the above into a coherent narrative. Walk through the logic chain step by step.

Rules:
- Be SPECIFIC: reference actual indicator values, dates, and price levels
- Be QUANTITATIVE: use numbers, not adjectives
- When signals conflict, explain WHY and which side has more weight
- Output ONLY valid JSON. No markdown, no extra text.
- All text fields must be detailed — minimum 2-3 sentences each. No one-liners.
- Do NOT give investment advice. This is for informational purposes only."""


def build_analysis_prompt(
    df,
    ticker: str,
    timeframe: str = "short",
    company_name: str = "",
) -> str:
    price_summary = get_price_summary(df)
    indicators_full = get_indicators_with_descriptions(df)

    tf_config = settings.TIMEFRAMES.get(timeframe, settings.TIMEFRAMES["short"])
    name_str = f" ({company_name})" if company_name else ""

    prompt_parts = [
        f"Analyze {ticker}{name_str} for a {tf_config['name']} timeframe ({tf_config['description']}).",
        f"The prediction horizon is approximately {tf_config['days']} trading days.",
        "",
        "## Price Summary",
        json.dumps(price_summary, indent=2, ensure_ascii=False),
        "",
        "## ALL Technical Indicators (latest values)",
    ]

    # Send ALL indicator values, not just summary
    for name, info in sorted(indicators_full.items()):
        val = info.get("value")
        if val is not None:
            try:
                fval = float(val)
                if not (fval == fval) or abs(fval) == float('inf'):
                    continue
                prompt_parts.append(f"  {name}: {round(fval, 4)}")
            except (ValueError, TypeError):
                continue

    # Add descriptions for key indicators
    prompt_parts.append("")
    prompt_parts.append("## Indicator Reference")
    key_indicators = [
        "RSI", "MACD_line", "MACD_signal", "MACD_hist", "KD_K", "KD_D",
        "CCI", "WR", "OBV", "ATR", "EMV", "VWAP",
        "ICHIMOKU_TENKAN", "ICHIMOKU_KIJUN", "ICHIMOKU_SENKOU_A", "ICHIMOKU_SENKOU_B",
        "SAR", "DMI_ADX", "DMI_DMP", "DMI_DMN",
        "AR", "BR", "CR", "DMA", "DMA_AMA", "EMA_20", "EMA_60",
    ]
    for name in key_indicators:
        if name in indicators_full and indicators_full[name].get("description"):
            prompt_parts.append(f"  {name}: {indicators_full[name]['description']}")

    prompt_parts.append("")
    prompt_parts.append("## Recent Price Action (last 20 days)")

    recent = df.tail(20)
    for idx, row in recent.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        prompt_parts.append(
            f"  {date_str}: O={row['open']:.2f} H={row['high']:.2f} "
            f"L={row['low']:.2f} C={row['close']:.2f} V={row['volume']:,.0f}"
        )

    prompt_parts.append("")
    prompt_parts.append(f"Provide your comprehensive {tf_config['name']} analysis as JSON with ALL fields filled in detail.")

    return "\n".join(prompt_parts)
