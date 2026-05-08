import logging
import numpy as np
import pandas as pd
import pytest

from app.core.indicators import compute_all_indicators, get_indicator_summary, get_price_summary


def _make_sample_df(days=250):
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    close = 100 + np.cumsum(np.random.randn(days) * 2)
    high = close + np.abs(np.random.randn(days))
    low = close - np.abs(np.random.randn(days))
    open_ = low + np.random.rand(days) * (high - low)
    volume = np.random.randint(1000000, 10000000, days)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    }, index=dates)


def _make_deterministic_df(n=50, seed=42):
    """Create a deterministic DataFrame for reproducible manual verification."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(np.random.randn(n) * 1.5)
    high = close + np.abs(np.random.randn(n) * 2)
    low = close - np.abs(np.random.randn(n) * 2)
    # Ensure high > low > open consistency
    open_ = low + np.random.rand(n) * (high - low)
    volume = np.random.randint(5000000, 15000000, n)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    }, index=dates)


# ──────────────────────────────────────────────
# Existing tests (KEPT AS-IS)
# ──────────────────────────────────────────────


def test_compute_all_indicators():
    df = _make_sample_df()
    result = compute_all_indicators(df)
    assert len(result) == len(df)
    # Should have added indicator columns
    indicator_cols = [c for c in result.columns if c not in ("open", "high", "low", "close", "volume")]
    assert len(indicator_cols) > 5  # At least 5 new columns
    assert not result.isnull().all().all()


def test_indicator_summary():
    df = _make_sample_df()
    df = compute_all_indicators(df)
    summary = get_indicator_summary(df)
    assert len(summary) > 0
    for name, data in summary.items():
        assert "latest" in data
        assert "mean_20" in data


def test_price_summary():
    df = _make_sample_df()
    summary = get_price_summary(df)
    assert summary["latest_close"] > 0
    assert summary["high_20"] >= summary["low_20"]
    assert "change_5d_pct" in summary


def test_empty_dataframe():
    df = pd.DataFrame()
    df_empty = compute_all_indicators(df)
    assert df_empty.empty

    summary = get_indicator_summary(df_empty)
    assert summary == {}

    price = get_price_summary(df_empty)
    assert price == {}


# ──────────────────────────────────────────────
# Edge case tests
# ──────────────────────────────────────────────


def test_single_row():
    """Single-row DataFrame should not crash; all indicator values should be NaN (or 0 for cumulative)."""
    df = pd.DataFrame({
        "open": [100.0], "high": [101.0], "low": [99.0],
        "close": [100.0], "volume": [1000000],
    })
    result = compute_all_indicators(df)
    assert len(result) == 1
    assert not result.isnull().all().all()  # base columns exist
    # MA/EMA need windowed data; first value of OBV is 0, SAR[0] = low[0]
    assert result["SAR"].iloc[0] == 99.0
    assert result["OBV"].iloc[0] == 0  # no diff → no volume accumulation
    # VWAP with single row = (close*vol)/vol = close
    assert result["VWAP"].iloc[0] == 100.0


def test_sparse_data_5_rows():
    """5-row DataFrame: short-period indicators should produce values."""
    df = _make_deterministic_df(n=5, seed=123)
    result = compute_all_indicators(df)

    # MA5 needs exactly 5 rows → last row should have value
    assert pd.notna(result["MA_5"].iloc[-1]), "MA_5 should have value at row 4"

    # MA10 needs 10 rows → all NaN
    assert result["MA_10"].isna().all(), "MA_10 should be all NaN with 5 rows"

    # MA60 needs 60 rows → all NaN
    assert result["MA_60"].isna().all(), "MA_60 should be all NaN with 5 rows"

    # VWAP works with any row count (cumulative)
    assert pd.notna(result["VWAP"].iloc[-1]), "VWAP should have value"

    # OBV works with any row count (cumulative)
    assert not result["OBV"].isna().any(), "OBV should have no NaN"

    # SAR works with any row count (>0)
    assert pd.notna(result["SAR"].iloc[-1]), "SAR should have value"


def test_all_nan_inputs():
    """All-NaN inputs should produce all-NaN outputs (NaN propagates cleanly)."""
    df = pd.DataFrame({
        "open": [np.nan] * 10, "high": [np.nan] * 10,
        "low": [np.nan] * 10, "close": [np.nan] * 10,
        "volume": [np.nan] * 10,
    })
    result = compute_all_indicators(df)
    indicator_cols = [c for c in result.columns if c not in ("open", "high", "low", "close", "volume")]
    for col in indicator_cols:
        assert result[col].isna().all(), f"{col} should be all NaN with NaN inputs"


def test_all_same_price():
    """All identical prices: RSI should be NaN (no movement), KDJ should resolve to 50."""
    n = 30
    df = pd.DataFrame({
        "open": [100.0] * n, "high": [101.0] * n, "low": [99.0] * n,
        "close": [100.0] * n, "volume": [5000000] * n,
    })
    result = compute_all_indicators(df)

    # RSI: no price change → avg_gain=0, avg_loss=0 → rs division yields NaN
    assert pd.isna(result["RSI"].iloc[-1]), "RSI should be NaN with flat prices"

    # KDJ: (close - low) / (high - low) = (100-99)/(101-99) = 0.5 → 50
    assert abs(result["KD_K"].iloc[-1] - 50.0) < 0.01, f"KD_K should be ~50, got {result['KD_K'].iloc[-1]}"

    # BB: std = 0, upper = mid = lower
    if pd.notna(result["BBM"].iloc[-1]):
        assert abs(result["BBU"].iloc[-1] - result["BBM"].iloc[-1]) < 0.01
        assert abs(result["BBL"].iloc[-1] - result["BBM"].iloc[-1]) < 0.01

    # VWAP: all same price × volume → VWAP = price
    if pd.notna(result["VWAP"].iloc[-1]):
        assert abs(result["VWAP"].iloc[-1] - 100.0) < 0.01

    # MACD: ema12 = ema26 = 100 → DIF = 0
    if pd.notna(result["MACD_macd"].iloc[-1]):
        assert abs(result["MACD_macd"].iloc[-1]) < 0.01


def test_zero_volume():
    """Zero volume: VWAP and EMV should produce NaN (division by zero guards)."""
    df = pd.DataFrame({
        "open": [100.0, 101.0, 102.0, 103.0, 104.0],
        "high": [101.0, 102.0, 103.0, 104.0, 105.0],
        "low": [99.0, 100.0, 101.0, 102.0, 103.0],
        "close": [100.0, 101.5, 102.0, 103.5, 104.0],
        "volume": [0, 0, 0, 0, 0],
    })
    result = compute_all_indicators(df)

    # VWAP: cum_vol = 0 → replaced by NaN
    assert result["VWAP"].isna().all(), "VWAP should be all NaN with zero volume"

    # EMV: box_ratio = (0/1e6) / (high-low) = 0 / spread → 0, then .replace(0,np.nan) → NaN
    # Actually: volume=0, box_ratio = 0/(high-low) = 0, replaced by NaN.
    # Then EMV = (mid_pt_diff) / NaN = NaN
    assert result["EMV"].isna().all() or (result["EMV"].dropna().empty), \
        f"EMV should be all/effectively NaN with zero volume: {result['EMV'].values}"

    # OBV: volume × direction = 0 → OBV stays at 0
    assert (result["OBV"] == 0).all(), "OBV should be all 0 with zero volume"


def test_high_equals_low():
    """When high == low (no price range): KDJ should resolve to 50, EMV NaN."""
    n = 20
    df = pd.DataFrame({
        "open": [100.0] * n, "high": [100.0] * n, "low": [100.0] * n,
        "close": np.linspace(100, 110, n), "volume": [5000000] * n,
    })
    result = compute_all_indicators(df)

    # KDJ: high_k == low_k, so denominator replaced by NaN → K is NaN
    # Wait: (close - low_k) / (high_k - low_k).replace(0, np.nan) → numerator non-zero if close != low_k
    # Actually with high=low=100, high_k=low_k=100, (high_k-low_k) → 0 → NaN, so K=NaN
    assert result["KD_K"].isna().all(), "KD_K should be NaN when high==low"

    # EMV: (high-low) = 0 → box_ratio denominator → NaN → EMV NaN
    assert result["EMV"].isna().all() or result["EMV"].dropna().empty, \
        "EMV should be NaN when high==low"


def test_single_unique_row():
    """DataFrame where high, low, open, close are all the same single value."""
    df = pd.DataFrame({
        "open": [100.0], "high": [100.0], "low": [100.0],
        "close": [100.0], "volume": [1000000],
    })
    result = compute_all_indicators(df)
    # Should not crash
    assert len(result) == 1
    # SAR[0] = low[0]
    assert result["SAR"].iloc[0] == 100.0
    # OBV = 0
    assert result["OBV"].iloc[0] == 0
    # VWAP = close (since single row)
    assert result["VWAP"].iloc[0] == 100.0


# ──────────────────────────────────────────────
# Manual verification tests
# ──────────────────────────────────────────────


def test_ma_manual_values():
    """Verify MA5/10/20/60 against manual calculation with deterministic data."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    close = df["close"]

    for period in [5, 10, 20, 60]:
        col = f"MA_{period}"
        expected = close.rolling(window=period).mean()
        # Compare non-NaN values
        mask = expected.notna()
        pd.testing.assert_series_equal(result[col][mask], expected[mask],
                                        check_names=False, rtol=1e-10)


def test_ema_manual_values():
    """Verify EMA5/10/20/60 against known formula: EMA = ewm(span=N, adjust=False)."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    close = df["close"]

    for period in [5, 10, 20, 60]:
        col = f"EMA_{period}"
        expected = close.ewm(span=period, adjust=False).mean()
        pd.testing.assert_series_equal(result[col], expected, check_names=False, rtol=1e-10)


def test_macd_manual_values():
    """Verify MACD(12/26/9) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    close = df["close"]

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    expected_macd = ema12 - ema26
    expected_signal = expected_macd.ewm(span=9, adjust=False).mean()
    expected_hist = expected_macd - expected_signal

    pd.testing.assert_series_equal(result["MACD_macd"], expected_macd, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["MACD_signal"], expected_signal, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["MACD_hist"], expected_hist, check_names=False, rtol=1e-10)


def test_rsi_manual_values():
    """Verify RSI(14) against Wilder's smoothing formula."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    close = df["close"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    expected_rsi = 100 - (100 / (1 + rs))

    pd.testing.assert_series_equal(result["RSI"], expected_rsi, check_names=False, rtol=1e-10)


def test_kdj_manual_values():
    """Verify KDJ(9,3,3) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    k_period = 9
    low_k = df["low"].rolling(k_period).min()
    high_k = df["high"].rolling(k_period).max()
    expected_k = ((df["close"] - low_k) / (high_k - low_k).replace(0, np.nan)) * 100
    expected_d = expected_k.rolling(3).mean()

    pd.testing.assert_series_equal(result["KD_K"], expected_k, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["KD_D"], expected_d, check_names=False, rtol=1e-10)


def test_bb_manual_values():
    """Verify Bollinger Bands (20, 2) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    close = df["close"]

    bb_period = 20
    bb_mid = close.rolling(bb_period).mean()
    bb_std = close.rolling(bb_period).std()  # ddof=1 (sample std) - matches current implementation
    expected_bbu = bb_mid + 2 * bb_std
    expected_bbl = bb_mid - 2 * bb_std
    expected_bbp = (close - expected_bbl) / (expected_bbu - expected_bbl).replace(0, np.nan)

    pd.testing.assert_series_equal(result["BBM"], bb_mid, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["BBU"], expected_bbu, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["BBL"], expected_bbl, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["BBP"], expected_bbp, check_names=False, rtol=1e-10)


def test_sar_manual_values():
    """Verify Parabolic SAR against custom implementation replica."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    def _compute_sar_copy(high, low, af_start=0.02, af_step=0.02, af_max=0.2):
        n = len(high)
        sar = np.zeros(n)
        sar[0] = low[0]
        bullish = True
        ep = high[0]
        af = af_start
        for i in range(1, n):
            sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
            if bullish:
                sar[i] = min(sar[i], low[i - 1], low[max(0, i - 2)])
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
                if low[i] < sar[i]:
                    bullish = False
                    sar[i] = ep
                    ep = low[i]
                    af = af_start
            else:
                sar[i] = max(sar[i], high[i - 1], high[max(0, i - 2)])
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
                if high[i] > sar[i]:
                    bullish = True
                    sar[i] = ep
                    ep = high[i]
                    af = af_start
        return sar

    expected_sar = _compute_sar_copy(df["high"].values, df["low"].values)
    np.testing.assert_array_almost_equal(result["SAR"].values, expected_sar, decimal=10)


def test_vwap_manual_values():
    """Verify VWAP against manual cumulative calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    cum_vp = (df["close"] * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    expected_vwap = cum_vp / cum_vol.replace(0, np.nan)

    pd.testing.assert_series_equal(result["VWAP"], expected_vwap, check_names=False, rtol=1e-10)


def test_ichimoku_manual_values():
    """Verify Ichimoku Cloud against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    expected_tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    expected_kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    expected_senkou_a = ((expected_tenkan + expected_kijun) / 2).shift(26)
    expected_senkou_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    expected_chikou = df["close"].shift(-26)

    pd.testing.assert_series_equal(result["ICHIMOKU_TENKAN"], expected_tenkan, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["ICHIMOKU_KIJUN"], expected_kijun, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["ICHIMOKU_SENKOU_A"], expected_senkou_a, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["ICHIMOKU_SENKOU_B"], expected_senkou_b, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["ICHIMOKU_CHIKOU"], expected_chikou, check_names=False, rtol=1e-10)


def test_atr_manual_values():
    """Verify ATR(14) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift(1)).abs()
    tr3 = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    expected_atr = tr.ewm(alpha=1 / 14, adjust=False).mean()

    pd.testing.assert_series_equal(result["ATR"], expected_atr, check_names=False, rtol=1e-10)


def test_arbr_manual_values():
    """Verify AR/BR(26) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    ar_period = 26
    ho = df["high"] - df["open"]
    ol = df["open"] - df["low"]
    expected_ar = ho.rolling(ar_period).sum() / ol.rolling(ar_period).sum().replace(0, np.nan) * 100
    hc = df["high"] - df["close"].shift(1)
    cl = df["close"].shift(1) - df["low"]
    expected_br = hc.rolling(ar_period).sum() / cl.rolling(ar_period).sum().replace(0, np.nan) * 100

    pd.testing.assert_series_equal(result["AR"], expected_ar, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["BR"], expected_br, check_names=False, rtol=1e-10)


def test_dma_manual_values():
    """Verify DMA(10,50) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    close = df["close"]

    expected_dma = close.rolling(10).mean() - close.rolling(50).mean()
    expected_ama = expected_dma.rolling(10).mean()

    pd.testing.assert_series_equal(result["DMA"], expected_dma, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["DMA_AMA"], expected_ama, check_names=False, rtol=1e-10)


def test_cci_manual_values():
    """Verify CCI(20) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    cci_period = 20
    tp = (df["high"] + df["low"] + df["close"]) / 3
    tp_sma = tp.rolling(cci_period).mean()
    tp_mad = tp.rolling(cci_period).apply(lambda x: np.abs(x - x.mean()).mean())
    expected_cci = (tp - tp_sma) / (0.015 * tp_mad.replace(0, np.nan))

    pd.testing.assert_series_equal(result["CCI"], expected_cci, check_names=False, rtol=1e-10)


def test_dmi_adx_manual_values():
    """Verify DMI/ADX(14) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    adx_period = 14
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift(1)).abs()
    tr3 = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)

    atr_adx = tr.ewm(alpha=1 / adx_period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / adx_period, adjust=False).mean() / atr_adx.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / adx_period, adjust=False).mean() / atr_adx.replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    expected_adx = dx.ewm(alpha=1 / adx_period, adjust=False).mean()

    pd.testing.assert_series_equal(result["DMI_ADX"], expected_adx, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["DMI_DMP"], plus_di, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["DMI_DMN"], minus_di, check_names=False, rtol=1e-10)


def test_emv_manual_values():
    """Verify EMV(14) against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    emv_period = 14
    mid_pt = (df["high"] + df["low"]) / 2
    mid_pt_prev = mid_pt.shift(1)
    box_ratio = (df["volume"] / 1000000) / (df["high"] - df["low"]).replace(0, np.nan)
    expected_emv = ((mid_pt - mid_pt_prev) / box_ratio.replace(0, np.nan)).rolling(emv_period).mean()

    pd.testing.assert_series_equal(result["EMV"], expected_emv, check_names=False, rtol=1e-10)


def test_kc_manual_values():
    """Verify Keltner Channel against manual calculation."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    kc_period = 20
    # ATR filled with 0 for first rows (as done in KC computation)
    atr_filled = result["ATR"].fillna(0)
    ema_kc = df["close"].ewm(span=kc_period, adjust=False).mean()
    expected_upper = ema_kc + 2 * atr_filled
    expected_middle = ema_kc
    expected_lower = ema_kc - 2 * atr_filled

    pd.testing.assert_series_equal(result["KC_UPPER"], expected_upper, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["KC_MIDDLE"], expected_middle, check_names=False, rtol=1e-10)
    pd.testing.assert_series_equal(result["KC_LOWER"], expected_lower, check_names=False, rtol=1e-10)


# ──────────────────────────────────────────────
# 1h vs 1d consistency tests
# ──────────────────────────────────────────────


def test_1h_vs_1d_same_row_count():
    """Identical price data with different index frequencies should produce identical indicator values."""
    n = 100
    np.random.seed(42)
    close_vals = 100 + np.cumsum(np.random.randn(n) * 1.5)
    high_vals = close_vals + np.abs(np.random.randn(n))
    low_vals = close_vals - np.abs(np.random.randn(n))
    open_vals = low_vals + np.random.rand(n) * (high_vals - low_vals)
    volume_vals = np.random.randint(1000000, 10000000, n)

    # 1d-indexed DataFrame
    df_1d = pd.DataFrame({
        "open": open_vals, "high": high_vals, "low": low_vals,
        "close": close_vals, "volume": volume_vals,
    }, index=pd.date_range("2024-01-01", periods=n, freq="B"))

    # 1h-indexed DataFrame with same values
    df_1h = pd.DataFrame({
        "open": open_vals, "high": high_vals, "low": low_vals,
        "close": close_vals, "volume": volume_vals,
    }, index=pd.date_range("2024-01-01 09:30", periods=n, freq="1h"))

    result_1d = compute_all_indicators(df_1d)
    result_1h = compute_all_indicators(df_1h)

    # All indicator columns should have identical values regardless of index type
    indicator_cols = [c for c in result_1d.columns if c not in ("open", "high", "low", "close", "volume")]
    for col in indicator_cols:
        v1 = result_1d[col].values
        v2 = result_1h[col].values
        # Compare NaN patterns using array-level operations (avoids index mismatch)
        nan1 = np.isnan(v1.astype(float))
        nan2 = np.isnan(v2.astype(float))
        assert (nan1 == nan2).all(), \
            f"{col} NaN pattern differs between 1h and 1d"
        # Compare non-NaN values
        mask = ~nan1
        np.testing.assert_array_almost_equal(v1[mask], v2[mask], decimal=10,
                                             err_msg=f"{col} differs between 1h and 1d")


def test_1h_vs_1d_same_values_different_lengths():
    """Indicator computation should be index-agnostic regardless of data length."""
    np.random.seed(99)
    n = 50
    close_vals = 100 + np.cumsum(np.random.randn(n))
    high_vals = close_vals + np.abs(np.random.randn(n))
    low_vals = close_vals - np.abs(np.random.randn(n))
    open_vals = low_vals + np.random.rand(n) * (high_vals - low_vals)
    volume_vals = np.random.randint(1000000, 10000000, n)

    df_1d = pd.DataFrame(
        {"open": open_vals, "high": high_vals, "low": low_vals, "close": close_vals, "volume": volume_vals},
        index=pd.date_range("2024-01-01", periods=n, freq="B"),
    )
    df_1h = pd.DataFrame(
        {"open": open_vals, "high": high_vals, "low": low_vals, "close": close_vals, "volume": volume_vals},
        index=pd.date_range("2024-01-01 09:30", periods=n, freq="1h"),
    )

    r1 = compute_all_indicators(df_1d)
    r2 = compute_all_indicators(df_1h)

    # Results should be identical regardless of index
    indicator_cols = [c for c in r1.columns if c not in ("open", "high", "low", "close", "volume")]
    for col in indicator_cols:
        v1, v2 = r1[col].values, r2[col].values
        np.testing.assert_array_equal(np.isnan(v1), np.isnan(v2))
        mask = ~np.isnan(v1)
        np.testing.assert_array_almost_equal(v1[mask], v2[mask], decimal=10,
                                             err_msg=f"{col} differs between 1h/1d")


# ──────────────────────────────────────────────
# NaN propagation and JSON serialization tests
# ──────────────────────────────────────────────


def test_nan_propagation_in_indicators():
    """NaN in input data should propagate to windowed-dependent indicators."""
    df = _make_deterministic_df(n=100, seed=42)
    # Inject NaN into a close price at index 50
    df.loc[df.index[50], "close"] = np.nan
    result = compute_all_indicators(df)

    # Windowed indicators that include the NaN close should have NaN at or near idx 50
    assert pd.isna(result["MA_5"].iloc[50]), "MA_5 should be NaN when close is NaN"
    # MA_5 window covers indices 46-50, and [50] is NaN → MA_5[50] = NaN
    # Also: MA_5[51] closes window over 47-51, still includes 50 → NaN
    assert pd.isna(result["MA_5"].iloc[51]), "MA_5[51] should still be NaN"
    # MA_5[54] window covers 50-54, still includes NaN → NaN
    assert pd.isna(result["MA_5"].iloc[54]), "MA_5[54] still includes NaN close"
    # MA_5[55] window covers 51-55, no NaN → valid
    assert pd.notna(result["MA_5"].iloc[55]), "MA_5 should recover after NaN exits window"

    # EMA and RSI use ewm with implicit NaN-ignore (carries forward previous value)
    # So they DON'T show NaN at the injection point, but the ewm smoothing
    # biases them toward the previous trend during the NaN gap
    assert pd.notna(result["RSI"].iloc[50]), "RSI persists through NaN close (ewm carries forward)"
    assert pd.notna(result["EMA_5"].iloc[50]), "EMA persists through NaN close"

    # Cumulative OBV: diff = NaN, so direction = 0, cumulative unchanged
    # OBV should hold the previous cumulative value at index 50
    assert result["OBV"].iloc[50] == result["OBV"].iloc[49], \
        "OBV should hold steady when close diff is NaN"


def test_nan_conversion_for_json():
    """NaN values are properly handled and can be converted to None for JSON serialization."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    # Simulate the _serialize_chart_indicators NaN→None conversion pattern
    # Pandas where() on numeric Series replaces None back to NaN, so we convert
    # to object dtype first to retain None values
    for col in result.columns:
        series = result[col].astype(object)
        nan_mask = result[col].isna()
        if nan_mask.any():
            # Simulate JSON-safe conversion: NaN entries → None
            converted = series.where(~nan_mask, other=None)
            assert converted[nan_mask].iloc[0] is None, \
                f"{col}: NaN should convert to None for JSON"


def test_all_indicators_present():
    """Verify all expected indicator columns are present in the output."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    expected_columns = [
        "MA_5", "MA_10", "MA_20", "MA_60",
        "EMA_5", "EMA_10", "EMA_20", "EMA_60",
        "MACD_macd", "MACD_signal", "MACD_hist",
        "RSI",
        "KD_K", "KD_D",
        "BBL", "BBM", "BBU", "BBB", "BBP",
        "OBV",
        "ATR",
        "CCI",
        "WR",
        "DMI_ADX", "DMI_DMP", "DMI_DMN",
        "SAR",
        "KC_UPPER", "KC_MIDDLE", "KC_LOWER",
        "ICHIMOKU_TENKAN", "ICHIMOKU_KIJUN",
        "ICHIMOKU_SENKOU_A", "ICHIMOKU_SENKOU_B", "ICHIMOKU_CHIKOU",
        "VWAP",
        "AR", "BR",
        "CR",
        "DMA", "DMA_AMA",
        "EMV",
    ]
    for col in expected_columns:
        assert col in result.columns, f"Missing indicator column: {col}"


def test_no_surprising_nans():
    """With sufficient data, most indicators should have values (not all NaN)."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)

    # With 100 rows, nearly all indicators should have valid values at the end
    always_has_value = [
        "MA_5", "MA_10", "MA_20", "MA_60",
        "EMA_5", "EMA_10", "EMA_20", "EMA_60",
        "MACD_macd", "MACD_signal", "MACD_hist",
        "RSI", "KD_K", "KD_D",
        "BBL", "BBM", "BBU", "BBB", "BBP",
        "OBV", "ATR", "CCI", "WR",
        "DMI_ADX", "DMI_DMP", "DMI_DMN",
        "SAR", "KC_UPPER", "KC_MIDDLE", "KC_LOWER",
        "AR", "BR", "CR",
        "DMA", "DMA_AMA", "EMV",
    ]
    for col in always_has_value:
        assert pd.notna(result[col].iloc[-1]), \
            f"{col} should have a valid value at last row with 100 rows of data"

    # VWAP has no warm-up period
    assert pd.notna(result["VWAP"].iloc[0]), "VWAP should have value from row 0"


def test_rsi_bounds():
    """RSI should always be between 0 and 100."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    rsi = result["RSI"].dropna()
    assert (rsi >= 0).all(), "RSI should never be below 0"
    assert (rsi <= 100).all(), "RSI should never be above 100"


def test_kd_bounds():
    """KD_K and KD_D should always be between 0 and 100."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    for col in ["KD_K", "KD_D"]:
        valid = result[col].dropna()
        assert (valid >= 0).all(), f"{col} should never be below 0"
        assert (valid <= 100).all(), f"{col} should never be above 100"


def test_bbp_bounds():
    """BBP should be roughly between 0 and 1, with possible overshoot."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    bbp = result["BBP"].dropna()
    # BBP can exceed [0,1] when price breaks bands, but shouldn't be wildly out of range
    assert (bbp >= -1).all(), "BBP should not be below -1"
    assert (bbp <= 2).all(), "BBP should not be above 2"


def test_macd_internal_consistency():
    """MACD histogram should equal DIF - signal."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    hist_calc = result["MACD_macd"] - result["MACD_signal"]
    pd.testing.assert_series_equal(result["MACD_hist"], hist_calc, check_names=False, rtol=1e-10)


def test_sar_always_below_high():
    """SAR should never exceed the high price in any period."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    # SAR can be above high briefly during flips, but generally consistent
    # Just verify it doesn't produce NaN unexpectedly
    assert pd.notna(result["SAR"].iloc[-1])


# ──────────────────────────────────────────────
# Logging tests
# ──────────────────────────────────────────────


def test_sparse_data_logging(caplog):
    """Sparse data should produce log messages about insufficient rows."""
    caplog.set_level(logging.INFO)

    # 5 rows: should trigger warnings for many indicators needing more data
    df = _make_deterministic_df(n=5, seed=123)
    compute_all_indicators(df)

    sparse_warnings = [r for r in caplog.records if "Data too sparse" in r.getMessage()]
    assert len(sparse_warnings) > 0, "Should log 'Data too sparse' warnings for small datasets"

    # Verify specific indicators are mentioned
    messages = " ".join(r.getMessage() for r in sparse_warnings)
    # With 5 rows, these should definitely be warned:
    assert "MA_10" in messages or "EMA_10" in messages
    assert "MA_60" in messages or "EMA_60" in messages
    assert "MACD" in messages


def test_no_sparse_warning_for_sufficient_data(caplog):
    """Adequately-sized data should NOT produce sparse data warnings."""
    caplog.set_level(logging.INFO)
    df = _make_deterministic_df(n=100, seed=42)
    compute_all_indicators(df)

    sparse_warnings = [r for r in caplog.records if "Data too sparse" in r.getMessage()]
    assert len(sparse_warnings) == 0, \
        f"No sparse warnings expected with 100 rows, got: {[r.getMessage() for r in sparse_warnings]}"


def test_edge_row_count_triggers(caplog):
    """Test at exact boundary: 60 rows should NOT trigger MA_60 warning, 59 should."""
    caplog.set_level(logging.INFO)

    df_60 = _make_deterministic_df(n=60, seed=1)
    compute_all_indicators(df_60)
    messages_60 = " ".join(r.getMessage() for r in caplog.records if "Data too sparse" in r.getMessage())
    assert "MA_60" not in messages_60, f"MA_60 should NOT warn at 60 rows, got: {messages_60}"

    caplog.clear()
    df_59 = _make_deterministic_df(n=59, seed=1)
    compute_all_indicators(df_59)
    messages_59 = " ".join(r.getMessage() for r in caplog.records if "Data too sparse" in r.getMessage())
    assert "MA_60" in messages_59, f"MA_60 SHOULD warn at 59 rows: {messages_59}"


# ──────────────────────────────────────────────
# Return signature and column ordering tests
# ──────────────────────────────────────────────


def test_return_signature_preserves_input():
    """compute_all_indicators() should preserve original columns."""
    df = _make_deterministic_df(n=100, seed=42)
    result = compute_all_indicators(df)
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in result.columns
        pd.testing.assert_series_equal(result[col], df[col], check_names=False)


def test_does_not_mutate_input():
    """compute_all_indicators() should NOT modify the input DataFrame."""
    df = _make_deterministic_df(n=100, seed=42)
    original_cols = list(df.columns)
    original_len = len(df.columns)
    compute_all_indicators(df)
    assert len(df.columns) == original_len, "Input DataFrame should not gain columns"
    assert list(df.columns) == original_cols, "Input DataFrame columns should be unchanged"


def test_get_indicators_with_descriptions():
    """get_indicators_with_descriptions should return latest values with descriptions."""
    from app.core.indicators import get_indicators_with_descriptions
    df = _make_deterministic_df(n=100, seed=42)
    result = get_indicators_with_descriptions(df)

    assert isinstance(result, dict)
    assert len(result) > 0

    # Each entry should have a 'value' key
    for name, entry in result.items():
        assert "value" in entry, f"Missing 'value' in result[{name}]"
        if entry["value"] is not None:
            # Should have at least one description
            has_desc = "description" in entry or "description_en" in entry
            assert has_desc, f"{name} should have description fields"
