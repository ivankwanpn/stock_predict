import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.routers.stock import _to_list, _to_time_series, _serialize_chart_indicators


client = TestClient(app)


def _make_sample_df(days=60):
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


def test_to_list_with_nan():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
    assert _to_list("a", df) == [1.0, None, 3.0]


def test_to_list_missing_column():
    df = pd.DataFrame({"a": [1.0, 2.0]})
    assert _to_list("b", df) == []


def test_serialize_chart_indicators_structure():
    from app.core.indicators import compute_all_indicators

    df = _make_sample_df()
    ind_df = compute_all_indicators(df)
    result = _serialize_chart_indicators(ind_df)

    expected_keys = {
        "ma", "ema", "bb", "sar", "kc", "ichimoku",
        "vwap", "macd", "kdj", "arbr", "cr", "dma", "emv", "rsi",
    }
    assert set(result.keys()) == expected_keys

    assert set(result["ma"].keys()) == {"ma5", "ma10", "ma20", "ma60"}
    assert set(result["ema"].keys()) == {"ema5", "ema10", "ema20", "ema60"}
    assert set(result["bb"].keys()) == {"upper", "middle", "lower"}
    assert set(result["kc"].keys()) == {"upper", "middle", "lower"}
    assert set(result["ichimoku"].keys()) == {"tenkan", "kijun", "senkouA", "senkouB", "chikou"}
    assert set(result["macd"].keys()) == {"macd", "signal", "histogram"}
    assert set(result["kdj"].keys()) == {"k", "d", "j"}

    assert len(result["rsi"]) == len(ind_df)
    assert len(result["sar"]) == len(ind_df)

    k = result["kdj"]["k"]
    d = result["kdj"]["d"]
    j = result["kdj"]["j"]
    for i in range(len(ind_df)):
        if k[i] is not None and d[i] is not None:
            expected_j = round(3 * k[i]["value"] - 2 * d[i]["value"], 4)
            assert abs(j[i]["value"] - expected_j) < 1e-3
        else:
            assert j[i] is None


@patch("app.routers.stock.get_ohlcv_range")
@patch("app.routers.stock.compute_all_indicators")
def test_chart_data_happy_path(mock_compute, mock_fetch):
    df = _make_sample_df()
    from app.core.indicators import compute_all_indicators as real_compute
    ind_df = real_compute(df)

    mock_fetch.return_value = df
    mock_compute.return_value = ind_df

    response = client.get(
        "/api/stock/0700.HK/chart-data",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31", "granularity": "1d"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["ticker"] == "0700.HK"
    assert data["granularity"] == "1d"
    assert len(data["ohlcv"]) == len(df)
    assert data["ohlcv"][0]["date"] == "2024-01-01"
    assert set(data["ohlcv"][0].keys()) == {"date", "open", "high", "low", "close", "volume"}

    ind = data["indicators"]
    assert set(ind.keys()) == {
        "ma", "ema", "bb", "sar", "kc", "ichimoku",
        "vwap", "macd", "kdj", "arbr", "cr", "dma", "emv", "rsi",
    }

    # Verify indicator items are {time, value} objects
    rsi = ind["rsi"]
    non_null = [x for x in rsi if x is not None]
    assert non_null, "Expected at least one non-null RSI value"
    assert isinstance(non_null[0], dict)
    assert set(non_null[0].keys()) == {"time", "value"}
    assert isinstance(non_null[0]["time"], str)
    assert isinstance(non_null[0]["value"], (int, float))


@patch("app.routers.stock.get_ohlcv_range")
def test_chart_data_1h_granularity(mock_fetch):
    df = _make_sample_df(days=10)
    mock_fetch.return_value = df

    response = client.get(
        "/api/stock/0700.HK/chart-data",
        params={"start_date": "2024-01-01", "end_date": "2024-01-05", "granularity": "1h"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "1h"
    assert "T" in data["ohlcv"][0]["date"]


def test_chart_data_invalid_granularity():
    response = client.get(
        "/api/stock/0700.HK/chart-data",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31", "granularity": "1w"},
    )
    assert response.status_code == 400
    assert "Invalid granularity" in response.json()["detail"]


def test_chart_data_missing_params():
    response = client.get("/api/stock/0700.HK/chart-data")
    assert response.status_code == 422


@patch("app.routers.stock.get_ohlcv_range")
def test_chart_data_invalid_ticker(mock_fetch):
    mock_fetch.side_effect = ValueError("No data returned")

    response = client.get(
        "/api/stock/INVALID/chart-data",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31", "granularity": "1d"},
    )
    assert response.status_code == 404


@patch("app.routers.stock.get_ohlcv_range")
def test_chart_data_upstream_failure(mock_fetch):
    mock_fetch.side_effect = RuntimeError("Upstream error")

    response = client.get(
        "/api/stock/0700.HK/chart-data",
        params={"start_date": "2024-01-01", "end_date": "2024-03-31", "granularity": "1d"},
    )
    assert response.status_code == 502
