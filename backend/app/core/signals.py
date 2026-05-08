from dataclasses import dataclass

import pandas as pd


@dataclass
class TechnicalSignal:
    ticker: str
    direction: str          # "bullish" | "bearish" | "neutral"
    confidence: float       # 0.0 - 100.0
    key_support: float
    key_resistance: float
    indicator_details: dict
    summary: str


def generate_signal(df: pd.DataFrame, ticker: str = "") -> TechnicalSignal:
    if df.empty:
        return TechnicalSignal(
            ticker=ticker,
            direction="neutral",
            confidence=0,
            key_support=0,
            key_resistance=0,
            indicator_details={},
            summary="Insufficient data",
        )

    latest = df.iloc[-1]
    score = 0.0
    max_score = 0.0
    details = {}

    # ──────────────────────────────────────────
    # 1. Oscillator Composite (weight 15)
    #    Merges RSI + KD(K) + CCI + WR into one
    # ──────────────────────────────────────────
    osc_score = 0.0
    osc_count = 0

    rsi_col = _find_col(df, "RSI")
    if rsi_col and pd.notna(latest.get(rsi_col)):
        rsi_val = float(latest[rsi_col])
        details["rsi"] = round(rsi_val, 1)
        if rsi_val < 30:
            osc_score += 15
        elif rsi_val < 40:
            osc_score += (40 - rsi_val) / 10 * 15
        elif rsi_val > 70:
            osc_score -= 15
        elif rsi_val > 60:
            osc_score -= (rsi_val - 60) / 10 * 15
        osc_count += 1

    k_col = _find_col(df, "KD_K")
    if k_col and pd.notna(latest.get(k_col)):
        k_val = float(latest[k_col])
        details["kd_k"] = round(k_val, 1)
        if k_val < 20:
            osc_score += 10
        elif k_val < 30:
            osc_score += (30 - k_val) / 10 * 10
        elif k_val > 80:
            osc_score -= 10
        elif k_val > 70:
            osc_score -= (k_val - 70) / 10 * 10
        osc_count += 1

    cci_col = _find_col(df, "CCI")
    if cci_col and pd.notna(latest.get(cci_col)):
        cci_val = float(latest[cci_col])
        details["cci"] = round(cci_val, 1)
        if cci_val < -100:
            osc_score += 10
        elif cci_val < -50:
            osc_score += (cci_val + 100) / 50 * 10
        elif cci_val > 100:
            osc_score -= 10
        elif cci_val > 50:
            osc_score -= (cci_val - 50) / 50 * 10
        osc_count += 1

    wr_col = _find_col(df, "WR")
    if wr_col and pd.notna(latest.get(wr_col)):
        wr_val = float(latest[wr_col])
        details["wr"] = round(wr_val, 1)
        if wr_val < -80:
            osc_score += 5
        elif wr_val > -20:
            osc_score -= 5
        osc_count += 1

    if osc_count > 0:
        osc_score /= osc_count
        details["oscillator_composite"] = round(osc_score, 1)
        score += osc_score * 0.75
        max_score += 15

    # ──────────────────────────────────────────
    # 2. MACD (weight 10)
    #    Crossover + histogram direction
    # ──────────────────────────────────────────
    macd_col = _find_col(df, "MACD_macd")
    macd_signal_col = _find_col(df, "MACD_signal")
    if macd_col and macd_signal_col and pd.notna(latest.get(macd_col)):
        macd_val = float(latest[macd_col])
        macd_signal_val = float(latest[macd_signal_col]) if pd.notna(latest.get(macd_signal_col)) else 0
        details["macd"] = round(macd_val, 4)
        max_score += 10
        if macd_val > macd_signal_val:
            score += 8
        else:
            score -= 8

        # Histogram direction (acceleration)
        hist_col = _find_col(df, "MACD_hist")
        if hist_col and pd.notna(latest.get(hist_col)):
            hist_val = float(latest[hist_col])
            prev_hist = float(df[hist_col].iloc[-2]) if len(df) >= 2 and pd.notna(df[hist_col].iloc[-2]) else 0
            if hist_val > prev_hist:
                score += 2
            elif hist_val < prev_hist:
                score -= 2

    # ──────────────────────────────────────────
    # 3. Moving Average Composite (weight 15)
    #    MA(5,10,20,60) + EMA(5,10,20,60)
    # ──────────────────────────────────────────
    ma_ema_bullish = 0
    ma_ema_count = 0
    for col_prefix in ["MA_", "EMA_"]:
        for col in df.columns:
            if col.startswith(col_prefix):
                val = latest[col]
                if pd.notna(val):
                    ma_ema_count += 1
                    if latest["close"] > float(val):
                        ma_ema_bullish += 1
                    details[f"price_vs_{col}"] = "above" if latest["close"] > float(val) else "below"

    if ma_ema_count >= 4:
        ratio = ma_ema_bullish / ma_ema_count
        score += (ratio - 0.5) * 30
        max_score += 15

    # ──────────────────────────────────────────
    # 4. ADX / DMI (non-additive filter + DI)
    #    ADX<20 → multiplier at the end
    #    DI+/DI- compared only when ADX>=20
    # ──────────────────────────────────────────
    adx_val_raw = None
    adx_col = _find_col(df, "DMI_ADX")
    di_plus_col = _find_col(df, "DMI_DMP")
    di_minus_col = _find_col(df, "DMI_DMN")

    if adx_col and pd.notna(latest.get(adx_col)):
        adx_val_raw = float(latest[adx_col])
        details["adx"] = round(adx_val_raw, 1)

    if di_plus_col and di_minus_col:
        di_plus = float(latest[di_plus_col]) if pd.notna(latest.get(di_plus_col)) else 0
        di_minus = float(latest[di_minus_col]) if pd.notna(latest.get(di_minus_col)) else 0
        if adx_val_raw is not None and adx_val_raw > 20:
            if di_plus > di_minus:
                score += 5
            else:
                score -= 5
            max_score += 5

    # ──────────────────────────────────────────
    # 5. Ichimoku (weight 15, NEW)
    #    Tenkan/Kijun cross + Price vs Cloud
    # ──────────────────────────────────────────
    tenkan_col = _find_col(df, "ICHIMOKU_TENKAN")
    kijun_col = _find_col(df, "ICHIMOKU_KIJUN")
    senkou_a_col = _find_col(df, "ICHIMOKU_SENKOU_A")
    senkou_b_col = _find_col(df, "ICHIMOKU_SENKOU_B")

    if tenkan_col and kijun_col and pd.notna(latest.get(tenkan_col)):
        tenkan = float(latest[tenkan_col])
        kijun = float(latest[kijun_col])
        max_score += 15

        # Tenkan/Kijun cross
        if tenkan > kijun:
            score += 7
        else:
            score -= 7

        # Price vs Cloud
        if senkou_a_col and senkou_b_col and pd.notna(latest.get(senkou_a_col)):
            senkou_a = float(latest[senkou_a_col])
            senkou_b = float(latest[senkou_b_col])
            cloud_top = max(senkou_a, senkou_b)
            cloud_bottom = min(senkou_a, senkou_b)
            if latest["close"] > cloud_top:
                score += 8
            elif latest["close"] < cloud_bottom:
                score -= 8

        details["ichimoku_tenkan_kijun"] = "bullish" if tenkan > kijun else "bearish"

    # ──────────────────────────────────────────
    # 6. SAR (weight 10, NEW)
    #    Price vs SAR line
    # ──────────────────────────────────────────
    sar_col = _find_col(df, "SAR")
    if sar_col and pd.notna(latest.get(sar_col)):
        sar_val = float(latest[sar_col])
        max_score += 10
        if latest["close"] > sar_val:
            score += 10
        else:
            score -= 10
        details["price_vs_sar"] = "above" if latest["close"] > sar_val else "below"

    # ──────────────────────────────────────────
    # 7. Volume Composite (weight 15, NEW)
    #    EMV + OBV trend + VWAP deviation
    # ──────────────────────────────────────────
    vol_score = 0
    vol_count = 0

    # EMV
    emv_col = _find_col(df, "EMV")
    if emv_col and pd.notna(latest.get(emv_col)):
        emv_val = float(latest[emv_col])
        if emv_val > 0:
            vol_score += 5
        else:
            vol_score -= 5
        details["emv"] = round(emv_val, 2)
        vol_count += 1

    # OBV trend
    obv_col = _find_col(df, "OBV")
    if obv_col and len(df) >= 10:
        obv_trend = df[obv_col].dropna()
        if len(obv_trend) >= 10:
            obv_rising = obv_trend.iloc[-1] > obv_trend.iloc[-10]
            details["obv_trend"] = "rising" if obv_rising else "falling"
            if obv_rising:
                vol_score += 5
            else:
                vol_score -= 5
            vol_count += 1

    # VWAP deviation
    vwap_col = _find_col(df, "VWAP")
    if vwap_col and pd.notna(latest.get(vwap_col)):
        vwap_val = float(latest[vwap_col])
        if latest["close"] > vwap_val:
            vol_score += 5
        else:
            vol_score -= 5
        details["price_vs_vwap"] = "above" if latest["close"] > vwap_val else "below"
        vol_count += 1

    if vol_count > 0:
        max_score += 15
        score += vol_score

    # ──────────────────────────────────────────
    # 8. Bollinger Bands (weight 10)
    #    Price position + bandwidth squeeze
    # ──────────────────────────────────────────
    bb_upper_col = _find_col(df, "BBU")
    bb_lower_col = _find_col(df, "BBL")
    if bb_lower_col and bb_upper_col and pd.notna(latest.get(bb_lower_col)):
        close = float(latest["close"])
        bb_low = float(latest[bb_lower_col])
        bb_high = float(latest[bb_upper_col])
        bb_position = (close - bb_low) / (bb_high - bb_low) * 100 if bb_high != bb_low else 50
        details["bb_position"] = round(bb_position, 1)
        max_score += 10
        if bb_position < 5:
            score += 10
        elif bb_position > 95:
            score -= 10
        else:
            # Graduated: closer to bottom = more bullish
            score += (50 - bb_position) / 50 * 5

        # Bandwidth (squeeze detection — informational only)
        bb_mid_col = _find_col(df, "BBM")
        if bb_mid_col and pd.notna(latest.get(bb_mid_col)):
            bandwidth = (bb_high - bb_low) / float(latest[bb_mid_col]) * 100
            details["bb_bandwidth"] = round(bandwidth, 2)

    # ──────────────────────────────────────────
    # 9. ADX Weak Trend Filter (applied at end)
    #    Halves all scores when ADX < 20
    # ──────────────────────────────────────────
    adx_multiplier = 1.0
    if adx_val_raw is not None and adx_val_raw < 20:
        adx_multiplier = 0.5
        details["adx_filter"] = "weak_trend"

    # ──────────────────────────────────────────
    # Final Scoring
    # ──────────────────────────────────────────
    max_score = max(max_score, 1)
    normalized = (score / max_score) * 100
    normalized *= adx_multiplier
    confidence = round(min(abs(normalized) * 2, 100), 1)

    if normalized > 15:
        direction = "bullish"
    elif normalized < -15:
        direction = "bearish"
    else:
        direction = "neutral"

    support, resistance = _compute_levels(df)

    return TechnicalSignal(
        ticker=ticker,
        direction=direction,
        confidence=confidence,
        key_support=support,
        key_resistance=resistance,
        indicator_details=details,
        summary=_build_summary(direction, confidence, details),
    )


def _compute_levels(df: pd.DataFrame) -> tuple[float, float]:
    recent = df.tail(20)
    support = round(float(recent["low"].min()), 2)
    resistance = round(float(recent["high"].max()), 2)

    close_col = "close" if "close" in df.columns else "Close"
    if close_col in df.columns:
        ma20 = df[close_col].tail(20).mean()
        if support > ma20:
            support = round(float(ma20), 2)
        if resistance < ma20:
            resistance = round(float(ma20), 2)

    return support, resistance


def _find_col(df: pd.DataFrame, *patterns: str) -> str | None:
    for pattern in patterns:
        for col in df.columns:
            if col.upper().startswith(pattern.upper()):
                return col
            if col.upper() == pattern.upper():
                return col
    return None


def _build_summary(direction: str, confidence: float, details: dict) -> str:
    dir_map = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}
    dir_cn = dir_map.get(direction, "中性")

    detail_str = ", ".join(f"{k}={v}" for k, v in list(details.items())[:5])
    return f"[技術軌] {dir_cn} (信心: {confidence:.0f}%) | {detail_str}"
