import asyncio

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import PriceSummaryResponse, HistoryResponse, IndicatorsResponse, ChartDataResponse
from app.services.data_service import fetch_ohlcv, get_company_name, get_price_summary, get_indicators_with_descriptions, get_ohlcv_range
from app.services.data_service import compute_all_indicators

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/{ticker}", response_model=PriceSummaryResponse)
async def get_stock_data(ticker: str):
    try:
        df = await asyncio.to_thread(fetch_ohlcv, ticker, "1y")
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ticker symbol or no data available.")

    company_name = await asyncio.to_thread(get_company_name, ticker)
    price_summary = get_price_summary(df)

    recent_candles = []
    for idx, row in df.tail(30).iterrows():
        recent_candles.append({
            "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
        })

    return PriceSummaryResponse(
        ticker=ticker,
        company_name=company_name,
        price_summary=price_summary,
        recent_candles=recent_candles,
    )


@router.get("/{ticker}/history", response_model=HistoryResponse)
async def get_stock_history(ticker: str, period: str = "2y", interval: str = "1d"):
    try:
        df = await asyncio.to_thread(fetch_ohlcv, ticker, period, interval)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ticker symbol or no data available.")
    except RuntimeError:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data from upstream for ticker '{ticker}'.")

    # Resample daily data to coarser intervals (yfinance often returns daily for HK stocks)
    _resample_map = {
        "1wk": "W",
        "1mo": "ME",
        "3mo": "QE",
        "1y": "YE",
    }
    if interval in _resample_map:
        df = df.resample(_resample_map[interval]).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()

    is_intraday = interval == "1h"
    data = []
    for idx, row in df.iterrows():
        if hasattr(idx, "strftime"):
            date_val = int(idx.timestamp()) if is_intraday else idx.strftime("%Y-%m-%d")
        else:
            date_val = str(idx)
        data.append({
            "date": date_val,
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
        })

    return HistoryResponse(ticker=ticker, data=data)


@router.get("/{ticker}/indicators", response_model=IndicatorsResponse)
async def get_stock_indicators(ticker: str):
    """Returns ALL computed technical indicators with educational descriptions."""
    try:
        df = await asyncio.to_thread(fetch_ohlcv, ticker, "1y")
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ticker symbol or no data available.")

    price_summary = get_price_summary(df)
    indicators = get_indicators_with_descriptions(df)

    return IndicatorsResponse(
        ticker=ticker,
        price_summary=price_summary,
        indicators=indicators,
    )


def _to_list(col, df):
    if col in df.columns:
        return [None if pd.isna(v) else round(float(v), 4) for v in df[col].tolist()]
    return []


def _to_time_series(col: str, df: pd.DataFrame) -> list:
    """Convert DataFrame column to list of {time, value} dicts for JSON serialization."""
    if col not in df.columns:
        return []
    result = []
    for idx, v in zip(df.index, df[col]):
        if pd.isna(v):
            result.append(None)
        else:
            time_str = idx.isoformat() if hasattr(idx, 'isoformat') else str(idx)
            result.append({"time": time_str, "value": round(float(v), 4)})
    return result


def _serialize_chart_indicators(df):
    # KD_J is now computed in indicators.py alongside KD_K and KD_D
    return {
        "ma": {
            "ma5": _to_time_series("MA_5", df),
            "ma10": _to_time_series("MA_10", df),
            "ma20": _to_time_series("MA_20", df),
            "ma60": _to_time_series("MA_60", df),
        },
        "ema": {
            "ema5": _to_time_series("EMA_5", df),
            "ema10": _to_time_series("EMA_10", df),
            "ema20": _to_time_series("EMA_20", df),
            "ema60": _to_time_series("EMA_60", df),
        },
        "bb": {
            "upper": _to_time_series("BBU", df),
            "middle": _to_time_series("BBM", df),
            "lower": _to_time_series("BBL", df),
        },
        "sar": _to_time_series("SAR", df),
        "kc": {
            "upper": _to_time_series("KC_UPPER", df),
            "middle": _to_time_series("KC_MIDDLE", df),
            "lower": _to_time_series("KC_LOWER", df),
        },
        "ichimoku": {
            "tenkan": _to_time_series("ICHIMOKU_TENKAN", df),
            "kijun": _to_time_series("ICHIMOKU_KIJUN", df),
            "senkouA": _to_time_series("ICHIMOKU_SENKOU_A", df),
            "senkouB": _to_time_series("ICHIMOKU_SENKOU_B", df),
            "chikou": _to_time_series("ICHIMOKU_CHIKOU", df),
        },
        "vwap": _to_time_series("VWAP", df),
        "macd": {
            "macd": _to_time_series("MACD_macd", df),
            "signal": _to_time_series("MACD_signal", df),
            "histogram": _to_time_series("MACD_hist", df),
        },
        "kdj": {
            "k": _to_time_series("KD_K", df),
            "d": _to_time_series("KD_D", df),
            "j": _to_time_series("KD_J", df),
        },
        "arbr": {
            "ar": _to_time_series("AR", df),
            "br": _to_time_series("BR", df),
        },
        "cr": _to_time_series("CR", df),
        "dma": {
            "dma": _to_time_series("DMA", df),
            "ama": _to_time_series("DMA_AMA", df),
        },
        "emv": _to_time_series("EMV", df),
        "rsi": _to_time_series("RSI", df),
    }


@router.get("/{ticker}/chart-data", response_model=ChartDataResponse)
async def get_chart_data(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: str = Query("1d", description="Bar granularity: '1h' or '1d'"),
):
    """Returns unified OHLCV data plus all pre-computed technical indicators."""
    interval_map = {"1h": "1h", "1d": "1d"}
    if granularity not in interval_map:
        raise HTTPException(status_code=400, detail=f"Invalid granularity: '{granularity}'. Must be '1h' or '1d'.")

    interval = interval_map[granularity]

    try:
        df = await asyncio.to_thread(get_ohlcv_range, ticker, start_date, end_date, interval)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No data for ticker '{ticker}' in range {start_date} to {end_date}.")
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data from upstream for ticker '{ticker}'.")

    indicators_df = compute_all_indicators(df)

    is_intraday = granularity == "1h"
    ohlcv = []
    for idx, row in df.iterrows():
        if hasattr(idx, "strftime"):
            date_val = idx.isoformat() if is_intraday else idx.strftime("%Y-%m-%d")
        else:
            date_val = str(idx)
        ohlcv.append({
            "date": date_val,
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": int(row["volume"]),
        })

    indicators = _serialize_chart_indicators(indicators_df)

    return {
        "ticker": ticker,
        "granularity": granularity,
        "ohlcv": ohlcv,
        "indicators": indicators,
    }
