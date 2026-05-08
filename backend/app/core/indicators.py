import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    n_rows = len(df)

    # Log warnings when data is too sparse for certain indicators
    _warn_sparse_data(n_rows)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["volume"]

    # SMA: MA(5, 10, 20, 60)
    for period in [5, 10, 20, 60]:
        df[f"MA_{period}"] = close.rolling(window=period).mean()

    # EMA (5, 10, 20, 60)
    for period in [5, 10, 20, 60]:
        df[f"EMA_{period}"] = close.ewm(span=period, adjust=False).mean()

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD_macd"] = ema12 - ema26
    df["MACD_signal"] = df["MACD_macd"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD_macd"] - df["MACD_signal"]

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # Stochastic KD(9,3,3)
    k_period = 9
    low_k = low.rolling(window=k_period).min()
    high_k = high.rolling(window=k_period).max()
    df["KD_K"] = ((close - low_k) / (high_k - low_k).replace(0, np.nan)) * 100
    df["KD_D"] = df["KD_K"].rolling(window=3).mean()
    df["KD_J"] = 3 * df["KD_K"] - 2 * df["KD_D"]

    # Bollinger Bands (20, 2)
    bb_period = 20
    bb_mid = close.rolling(window=bb_period).mean()
    bb_std = close.rolling(window=bb_period).std()
    df["BBL"] = bb_mid - 2 * bb_std
    df["BBM"] = bb_mid
    df["BBU"] = bb_mid + 2 * bb_std
    df["BBB"] = (df["BBU"] - df["BBL"]) / bb_mid.replace(0, np.nan) * 100
    df["BBP"] = (close - df["BBL"]) / (df["BBU"] - df["BBL"]).replace(0, np.nan)

    # OBV
    obv = (volume * ((close.diff() > 0).astype(int) - (close.diff() < 0).astype(int))).cumsum()
    df["OBV"] = obv

    # ATR(14)
    atr_period = 14
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/atr_period, adjust=False).mean()

    # CCI(20)
    cci_period = 20
    tp = (high + low + close) / 3
    tp_sma = tp.rolling(window=cci_period).mean()
    tp_mad = tp.rolling(window=cci_period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df["CCI"] = (tp - tp_sma) / (0.015 * tp_mad.replace(0, np.nan))

    # Williams %R(14)
    wr_period = 14
    high_wr = high.rolling(window=wr_period).max()
    low_wr = low.rolling(window=wr_period).min()
    df["WR"] = ((high_wr - close) / (high_wr - low_wr).replace(0, np.nan)) * -100

    # DMI/ADX(14)
    adx_period = 14
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)

    atr_adx = tr.ewm(alpha=1/adx_period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/adx_period, adjust=False).mean() / atr_adx.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1/adx_period, adjust=False).mean() / atr_adx.replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    df["DMI_ADX"] = dx.ewm(alpha=1/adx_period, adjust=False).mean()
    df["DMI_DMP"] = plus_di
    df["DMI_DMN"] = minus_di

    # Parabolic SAR
    def _compute_sar(high, low, af_start=0.02, af_step=0.02, af_max=0.2):
        n = len(high)
        sar = np.zeros(n)
        sar[0] = low[0]
        bullish = True
        ep = high[0]
        af = af_start
        for i in range(1, n):
            sar[i] = sar[i-1] + af * (ep - sar[i-1])
            if bullish:
                sar[i] = min(sar[i], low[i-1], low[max(0, i-2)])
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
                if low[i] < sar[i]:
                    bullish = False
                    sar[i] = ep
                    ep = low[i]
                    af = af_start
            else:
                sar[i] = max(sar[i], high[i-1], high[max(0, i-2)])
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
                if high[i] > sar[i]:
                    bullish = True
                    sar[i] = ep
                    ep = high[i]
                    af = af_start
        return sar
    df["SAR"] = _compute_sar(high.values, low.values)

    # Keltner Channel (20, 2)
    kc_period = 20
    kc_atr = df["ATR"].fillna(0)
    ema_kc = close.ewm(span=kc_period, adjust=False).mean()
    df["KC_UPPER"] = ema_kc + 2 * kc_atr
    df["KC_MIDDLE"] = ema_kc
    df["KC_LOWER"] = ema_kc - 2 * kc_atr

    # Ichimoku Cloud (一目均衡表)
    tenkan_period = 9
    df["ICHIMOKU_TENKAN"] = (high.rolling(tenkan_period).max() + low.rolling(tenkan_period).min()) / 2
    kijun_period = 26
    df["ICHIMOKU_KIJUN"] = (high.rolling(kijun_period).max() + low.rolling(kijun_period).min()) / 2
    df["ICHIMOKU_SENKOU_A"] = ((df["ICHIMOKU_TENKAN"] + df["ICHIMOKU_KIJUN"]) / 2).shift(26)
    senkou_period = 52
    df["ICHIMOKU_SENKOU_B"] = ((high.rolling(senkou_period).max() + low.rolling(senkou_period).min()) / 2).shift(26)
    df["ICHIMOKU_CHIKOU"] = close.shift(-26)

    # VWAP (Volume Weighted Average Price)
    cum_vp = (close * volume).cumsum()
    cum_vol = volume.cumsum()
    df["VWAP"] = cum_vp / cum_vol.replace(0, np.nan)

    # ARBR (人氣意願指標)
    ar_period = 26
    ho = high - open_
    ol = open_ - low
    df["AR"] = ho.rolling(ar_period).sum() / ol.rolling(ar_period).sum().replace(0, np.nan) * 100
    hc = high - close.shift(1)
    cl = close.shift(1) - low
    df["BR"] = hc.rolling(ar_period).sum() / cl.rolling(ar_period).sum().replace(0, np.nan) * 100

    # CR (能量指標)
    cr_period = 26
    mid = (high + low + close) / 3
    prev_mid = mid.shift(1)
    up_cr = high - prev_mid
    down_cr = prev_mid - low
    up_sum = up_cr.clip(lower=0).rolling(cr_period).sum()
    down_sum = down_cr.clip(lower=0).rolling(cr_period).sum()
    df["CR"] = up_sum / down_sum.replace(0, np.nan) * 100

    # DMA (Difference of Moving Average)
    df["DMA"] = close.rolling(10).mean() - close.rolling(50).mean()
    df["DMA_AMA"] = df["DMA"].rolling(10).mean()

    # EMV (Ease of Movement Value)
    emv_period = 14
    mid_pt = (high + low) / 2
    mid_pt_prev = mid_pt.shift(1)
    box_ratio = (volume / 1000000) / (high - low).replace(0, np.nan)
    df["EMV"] = ((mid_pt - mid_pt_prev) / box_ratio.replace(0, np.nan)).rolling(emv_period).mean()

    return df


def _warn_sparse_data(n_rows: int) -> None:
    """Log warnings when the dataset has too few rows for certain indicators."""
    indicator_min_rows = {
        "MA_5 / EMA_5": 5,
        "KD_K / KD_D": 10,
        "MA_10 / EMA_10": 10,
        "RSI": 15,
        "MACD (12/26/9)": 27,
        "MA_20 / EMA_20 / BB / CCI / KC": 20,
        "ATR / WR / EMV / DMI_ADX": 15,
        "AR / BR / CR": 28,
        "DMA": 51,
        "MA_60 / EMA_60": 60,
        "ICHIMOKU": 53,
    }
    for indicator, min_rows in indicator_min_rows.items():
        if n_rows < min_rows:
            logger.info(
                "Data too sparse for %s: need >= %d rows, got %d. Output will be NaN.",
                indicator, min_rows, n_rows,
            )


def get_indicator_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    latest = df.iloc[-1]
    summary = {}

    indicator_cols = _get_indicator_columns(df)

    for name, col in indicator_cols.items():
        if col in df.columns:
            series = df[col].dropna()
            if not series.empty:
                summary[name] = {
                    "latest": round(float(series.iloc[-1]), 4),
                    "mean_20": round(float(series.tail(20).mean()), 4),
                    "min_20": round(float(series.tail(20).min()), 4),
                    "max_20": round(float(series.tail(20).max()), 4),
                }

    return summary


def get_price_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    latest = df.iloc[-1]
    recent = df.tail(20)

    change_5d = None
    if len(df) >= 6:
        change_5d = round(float((df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100), 2)

    change_20d = None
    if len(df) >= 21:
        change_20d = round(float((df["close"].iloc[-1] / df["close"].iloc[-21] - 1) * 100), 2)

    return {
        "latest_close": round(float(latest["close"]), 2),
        "latest_open": round(float(latest["open"]), 2),
        "latest_high": round(float(latest["high"]), 2),
        "latest_low": round(float(latest["low"]), 2),
        "volume_latest": int(latest["volume"]),
        "avg_volume_20": int(recent["volume"].mean()),
        "high_20": round(float(recent["high"].max()), 2),
        "low_20": round(float(recent["low"].min()), 2),
        "change_5d_pct": change_5d,
        "change_20d_pct": change_20d,
    }


INDICATOR_GUIDE: dict[str, dict[str, str]] = {
    "MA_5": {
        "description": "5日移動平均線：短期趨勢指標。價格在MA上方為上升趨勢，下方為下降趨勢。",
        "description_en": "5-day moving average: short-term trend indicator. Price above MA suggests uptrend, below suggests downtrend.",
    },
    "MA_10": {
        "description": "10日移動平均線：短中期趨勢指標，常用於確認短期趨勢強度。",
        "description_en": "10-day moving average: short-to-mid term trend indicator, used to confirm short-term trend strength.",
    },
    "MA_20": {
        "description": "20日移動平均線：中期趨勢指標，價格在MA上方代表中期趨勢偏多。",
        "description_en": "20-day moving average: mid-term trend indicator. Price above suggests bullish mid-term trend.",
    },
    "MA_60": {
        "description": "60日移動平均線：長期趨勢指標，又稱季線，為多空分水嶺。",
        "description_en": "60-day moving average: long-term trend indicator, also known as the quarterly line, a bull/bear divide.",
    },
    "MACD_macd": {
        "description": "MACD快線(DIF)：快速EMA減慢速EMA，反映短期與長期動能差異。",
        "description_en": "MACD fast line (DIF): fast EMA minus slow EMA, reflects momentum divergence.",
    },
    "MACD_signal": {
        "description": "MACD慢線(信號線)：DIF的9日EMA，當DIF穿越信號線為買賣訊號。",
        "description_en": "MACD signal line: 9-day EMA of DIF. DIF crossing signal line generates trade signals.",
    },
    "MACD_hist": {
        "description": "MACD柱狀圖：DIF與信號線的差值，正值擴大代表多頭動能增強。",
        "description_en": "MACD histogram: difference between DIF and signal line. Positive widening indicates bullish momentum.",
    },
    "RSI": {
        "description": "相對強弱指數(0-100)：<30超賣(可能反彈)，>70超買(可能回調)，50以上偏強。",
        "description_en": "Relative Strength Index (0-100): <30 oversold (possible bounce), >70 overbought (possible pullback), above 50 is strong.",
    },
    "KD_K": {
        "description": "隨機指標K值(快線)：反映當前收盤價在近期價格區間的位置，>80超買，<20超賣。",
        "description_en": "Stochastic K-value (fast): reflects close price position in recent range. >80 overbought, <20 oversold.",
    },
    "KD_D": {
        "description": "隨機指標D值(慢線)：K值的3日平均，K穿越D為買賣訊號。",
        "description_en": "Stochastic D-value (slow): 3-day average of K. K crossing D generates trade signals.",
    },
    "KD_J": {
        "description": "隨機指標J值：J=3K-2D，>100為超買區，<0為超賣區，反應比K更靈敏。",
        "description_en": "Stochastic J-value: J=3K-2D, >100 overbought zone, <0 oversold zone, more sensitive than K.",
    },
    "BBL": {
        "description": "布林帶下軌：中軌減2倍標準差，價格觸及下軌可能超賣。",
        "description_en": "Bollinger Lower Band: middle band minus 2 standard deviations. Price touching lower band may indicate oversold.",
    },
    "BBM": {
        "description": "布林帶中軌：20日移動平均線，為趨勢參考線。",
        "description_en": "Bollinger Middle Band: 20-day moving average, serves as trend reference.",
    },
    "BBU": {
        "description": "布林帶上軌：中軌加2倍標準差，價格觸及上軌可能超買。",
        "description_en": "Bollinger Upper Band: middle band plus 2 standard deviations. Price touching upper band may indicate overbought.",
    },
    "BBB": {
        "description": "布林帶寬度(Bandwidth)：衡量波動性，頻道擴寬表示波動加劇。",
        "description_en": "Bollinger Bandwidth: measures volatility. Widening bands indicate increasing volatility.",
    },
    "BBP": {
        "description": "布林帶百分比位置(0-1)：價格在帶內的位置，>1為突破上軌，<0為跌破下軌。",
        "description_en": "Bollinger %B (0-1): position within bands. >1 means above upper band, <0 means below lower band.",
    },
    "OBV": {
        "description": "能量潮(On-Balance Volume)：量價累積指標，OBV上升確認上漲趨勢。",
        "description_en": "On-Balance Volume: cumulative volume indicator. Rising OBV confirms uptrend.",
    },
    "ATR": {
        "description": "平均真實波幅(Average True Range)：衡量市場波動程度，數值越大波動越劇烈。",
        "description_en": "Average True Range: measures market volatility. Higher values indicate more剧烈 volatility.",
    },
    "CCI": {
        "description": "順勢指標(Commodity Channel Index)：>100超買，< -100超賣，用於識別趨勢強度。",
        "description_en": "Commodity Channel Index: >100 overbought, <-100 oversold, used to identify trend strength.",
    },
    "WR": {
        "description": "威廉指標Williams %R(-100 to 0)：< -80超買(接近-100)，> -20超賣(接近0)。",
        "description_en": "Williams %R (-100 to 0): <-80 oversold (near -100), >-20 overbought (near 0).",
    },
    "DMI_ADX": {
        "description": "平均趨向指數ADX(0-100)：>25表示趨勢強勁，<20表示盤整無趨勢。",
        "description_en": "Average Directional Index (0-100): >25 indicates strong trend, <20 indicates ranging market.",
    },
    "DMI_DMP": {
        "description": "正趨向指標(+DI)：衡量上升動能，+DI > -DI 為多頭市場。",
        "description_en": "Positive Directional Indicator (+DI): measures upward momentum. +DI > -DI indicates bullish market.",
    },
    "DMI_DMN": {
        "description": "負趨向指標(-DI)：衡量下降動能，-DI > +DI 為空頭市場。",
        "description_en": "Negative Directional Indicator (-DI): measures downward momentum. -DI > +DI indicates bearish market.",
    },
    "EMA_5": {
        "description": "5日指數移動平均線：對近期價格變化反應更迅速，適合捕捉短期動能。",
        "description_en": "5-day Exponential Moving Average: responds faster to recent price changes, suitable for short-term momentum.",
    },
    "EMA_10": {
        "description": "10日指數移動平均線：短中期動能指標，EMA比SMA對價格變化更敏感。",
        "description_en": "10-day Exponential Moving Average: short-to-mid term momentum indicator, more sensitive than SMA.",
    },
    "EMA_20": {
        "description": "20日指數移動平均線：中期趨勢指標，常用於確認趨勢方向。",
        "description_en": "20-day Exponential Moving Average: mid-term trend indicator for trend direction confirmation.",
    },
    "EMA_60": {
        "description": "60日指數移動平均線：長期趨勢指標，EMA_60上揚代表長期趨勢偏多。",
        "description_en": "60-day Exponential Moving Average: long-term trend indicator. Rising EMA_60 suggests bullish bias.",
    },
    "SAR": {
        "description": "拋物線轉向指標(SAR)：追蹤止損工具，點位在價格下方為多頭，上方為空頭。",
        "description_en": "Parabolic SAR: trailing stop-loss tool. Dots below price suggest uptrend, above suggest downtrend.",
    },
    "KC_UPPER": {
        "description": "肯特納通道上軌：EMA加2倍ATR，突破上軌代表強勢上漲。",
        "description_en": "Keltner Channel Upper Band: EMA plus 2x ATR. Breaking above suggests strong upward movement.",
    },
    "KC_MIDDLE": {
        "description": "肯特納通道中軌：20日EMA，為通道基準線。",
        "description_en": "Keltner Channel Middle Band: 20-day EMA, serves as channel baseline.",
    },
    "KC_LOWER": {
        "description": "肯特納通道下軌：EMA減2倍ATR，跌破下軌代表強勢下跌。",
        "description_en": "Keltner Channel Lower Band: EMA minus 2x ATR. Breaking below suggests strong downward movement.",
    },
    "ICHIMOKU_TENKAN": {
        "description": "一目均衡表轉換線(9日高低中點)：短期趨勢指標，與基準線交叉為買賣訊號。",
        "description_en": "Ichimoku Tenkan-sen (9-period mid-point): short-term trend. Cross with Kijun-sen generates signals.",
    },
    "ICHIMOKU_KIJUN": {
        "description": "一目均衡表基準線(26日高低中點)：中期趨勢指標，價格在其上方為偏多。",
        "description_en": "Ichimoku Kijun-sen (26-period mid-point): mid-term trend. Price above suggests bullish bias.",
    },
    "ICHIMOKU_SENKOU_A": {
        "description": "一目均衡表先行A(未來雲層邊界1)：轉換線與基準線均值前移26日，構成雲層上緣。",
        "description_en": "Ichimoku Senkou Span A: (Tenkan+Kijun)/2 shifted 26d ahead, forms cloud upper boundary.",
    },
    "ICHIMOKU_SENKOU_B": {
        "description": "一目均衡表先行B(未來雲層邊界2)：52日高低中點前移26日，構成雲層下緣。",
        "description_en": "Ichimoku Senkou Span B: 52d mid-point shifted 26d ahead, forms cloud lower boundary.",
    },
    "ICHIMOKU_CHIKOU": {
        "description": "一目均衡表遅行線(當前收盤價後移26日)：驗證趨勢，與歷史價格比較判斷強弱。",
        "description_en": "Ichimoku Chikou Span: current close shifted 26d back, verifies trend against historical prices.",
    },
    "VWAP": {
        "description": "成交量加權平均價(VWAP)：機構常用參考價，價格在VWAP上方為強勢。",
        "description_en": "Volume Weighted Average Price: institutional reference. Price above VWAP is considered strong.",
    },
    "AR": {
        "description": "人氣指標AR(26日)：開盤價多空強度，AR>120過熱，AR<80過冷。",
        "description_en": "AR Indicator (26d): open-price strength. AR>120 overbought, AR<80 oversold.",
    },
    "BR": {
        "description": "意願指標BR(26日)：收盤價多空意願，BR>300極度過熱，BR<50極度過冷。",
        "description_en": "BR Indicator (26d): close-price willingness. BR>300 extremely overbought, BR<50 extremely oversold.",
    },
    "CR": {
        "description": "能量指標CR(26日)：中間價多空動能，CR>200過熱，CR<40過冷。",
        "description_en": "CR Momentum Indicator (26d): mid-price momentum. CR>200 overbought, CR<40 oversold.",
    },
    "DMA": {
        "description": "DMA(10日與50日均線差)：短期與長期均線差距，正值為多頭排列。",
        "description_en": "DMA (10d & 50d MA difference): gap between short and long MA. Positive = bullish alignment.",
    },
    "DMA_AMA": {
        "description": "DMA均線(AMA)：DMA的10日移動平均，用於判斷DMA趨勢方向。",
        "description_en": "DMA Moving Average (AMA): 10d MA of DMA, used to identify DMA trend direction.",
    },
    "EMV": {
        "description": "簡易波動指標(EMV)：量價波動關係，正值向上突破0軸為買入訊號。",
        "description_en": "Ease of Movement Value: price-volume relationship. Positive crossing above zero is a buy signal.",
    },
}


def get_indicators_with_descriptions(df: pd.DataFrame) -> dict[str, dict]:
    """Compute all indicators and return latest values paired with descriptions."""
    df = compute_all_indicators(df)
    if df.empty:
        return {}

    last_row = df.iloc[-1]
    result = {}
    indicator_cols = _get_indicator_columns(df)

    for name, col in indicator_cols.items():
        if col in df.columns:
            val = last_row[col]
            value = round(float(val), 4) if pd.notna(val) else None
        else:
            value = None

        guide = INDICATOR_GUIDE.get(col, {})
        entry = {"value": value}
        if guide.get("description"):
            entry["description"] = guide["description"]
        if guide.get("description_en"):
            entry["description_en"] = guide["description_en"]

        # Also match by the display name (e.g. "MA_5" might be under col "MA_5")
        if not guide and name in INDICATOR_GUIDE:
            guide = INDICATOR_GUIDE.get(name, {})
            if guide.get("description"):
                entry["description"] = guide["description"]
            if guide.get("description_en"):
                entry["description_en"] = guide["description_en"]

        result[name] = entry

    # Also include individual MA periods
    for col in df.columns:
        if col.startswith("MA_") and col not in result:
            guide = INDICATOR_GUIDE.get(col, {})
            val = last_row[col]
            value = round(float(val), 4) if pd.notna(val) else None
            entry = {"value": value}
            if guide.get("description"):
                entry["description"] = guide["description"]
            if guide.get("description_en"):
                entry["description_en"] = guide["description_en"]
            result[col] = entry

    return result


def _get_indicator_columns(df: pd.DataFrame) -> dict[str, str]:
    mapping = {}
    for col in df.columns:
        if col.startswith("MA_"):
            mapping["MA"] = col
        elif col.startswith("EMA_"):
            mapping["EMA"] = col
        elif col == "RSI":
            mapping["RSI"] = col
        elif col == "MACD_macd":
            mapping["MACD_line"] = col
        elif col == "MACD_signal":
            mapping["MACD_signal"] = col
        elif col == "MACD_hist":
            mapping["MACD_hist"] = col
        elif col == "BBL":
            mapping["BB_Lower"] = col
        elif col == "BBM":
            mapping["BB_Mid"] = col
        elif col == "BBU":
            mapping["BB_Upper"] = col
        elif col == "BBB":
            mapping["BB_Bandwidth"] = col
        elif col == "BBP":
            mapping["BB_Pct"] = col
        elif col == "OBV":
            mapping["OBV"] = col
        elif col == "ATR":
            mapping["ATR"] = col
        elif col == "CCI":
            mapping["CCI"] = col
        elif col == "WR":
            mapping["WR"] = col
        elif col == "DMI_ADX":
            mapping["DMI_ADX"] = col
        elif col == "DMI_DMP":
            mapping["DMI_DMP"] = col
        elif col == "DMI_DMN":
            mapping["DMI_DMN"] = col
        elif col == "KD_K":
            mapping["KD_K"] = col
        elif col == "KD_D":
            mapping["KD_D"] = col
        elif col == "KD_J":
            mapping["KD_J"] = col
        elif col == "SAR":
            mapping["SAR"] = col
        elif col == "KC_UPPER":
            mapping["KC_Upper"] = col
        elif col == "KC_MIDDLE":
            mapping["KC_Middle"] = col
        elif col == "KC_LOWER":
            mapping["KC_Lower"] = col
        elif col == "ICHIMOKU_TENKAN":
            mapping["Ichimoku_Tenkan"] = col
        elif col == "ICHIMOKU_KIJUN":
            mapping["Ichimoku_Kijun"] = col
        elif col == "ICHIMOKU_SENKOU_A":
            mapping["Ichimoku_SenkouA"] = col
        elif col == "ICHIMOKU_SENKOU_B":
            mapping["Ichimoku_SenkouB"] = col
        elif col == "ICHIMOKU_CHIKOU":
            mapping["Ichimoku_Chikou"] = col
        elif col == "VWAP":
            mapping["VWAP"] = col
        elif col == "AR":
            mapping["AR"] = col
        elif col == "BR":
            mapping["BR"] = col
        elif col == "CR":
            mapping["CR"] = col
        elif col == "DMA":
            mapping["DMA"] = col
        elif col == "DMA_AMA":
            mapping["DMA_AMA"] = col
        elif col == "EMV":
            mapping["EMV"] = col
    return mapping
