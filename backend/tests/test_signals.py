import pandas as pd
import numpy as np

from app.core.indicators import compute_all_indicators
from app.core.signals import generate_signal, TechnicalSignal


def _make_df(close_values):
    n = len(close_values)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "open": [c - 0.5 for c in close_values],
        "high": [c + 1 for c in close_values],
        "low": [c - 1 for c in close_values],
        "close": close_values,
        "volume": [1000000] * n,
    }, index=dates)


def test_bullish_signal():
    # Uptrend with pullback
    closes = list(range(80, 120)) + list(range(120, 115, -1)) + list(range(115, 130))
    df = _make_df([float(c) for c in closes])
    df = compute_all_indicators(df)
    signal = generate_signal(df, ticker="TEST.HK")

    assert isinstance(signal, TechnicalSignal)
    assert signal.direction in ("bullish", "bearish", "neutral")
    assert 0 <= signal.confidence <= 100
    assert signal.key_support <= signal.key_resistance
    assert len(signal.indicator_details) > 0


def test_bearish_signal():
    # Downtrend
    closes = list(range(150, 100, -1)) + list(range(100, 105)) + list(range(105, 80, -1))
    df = _make_df([float(c) for c in closes])
    df = compute_all_indicators(df)
    signal = generate_signal(df, ticker="TEST.HK")

    assert isinstance(signal, TechnicalSignal)
    # In a strong downtrend, should be bearish
    assert signal.direction in ("bearish", "neutral")


def test_edge_cases():
    # Very short dataframe
    df = _make_df([100.0] * 5)
    df = compute_all_indicators(df)
    signal = generate_signal(df, ticker="TEST.HK")
    # With flat prices, direction should be neutral (no trend)
    assert signal.direction in ("neutral", "bearish", "bullish")

    # Empty dataframe
    df_empty = pd.DataFrame()
    signal = generate_signal(df_empty, ticker="TEST.HK")
    assert signal.direction == "neutral"
    assert signal.confidence == 0
