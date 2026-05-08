import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
import yfinance as yf

from app.core.cache import Cache


_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 300  # 5 minutes


def _cache_get(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _cache[key]
    return None


def _cache_set(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


def fetch_ohlcv(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
    use_cache: bool = True,
) -> pd.DataFrame:

    if use_cache:
        cache = Cache()
        cached = cache.get(ticker, period, interval)
        if cached is not None:
            return cached

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
    except Exception as e:
        logging.error(
            "yfinance fetch failed for %s (period=%s, interval=%s): %s",
            ticker, period, interval, e,
        )
        raise RuntimeError(f"Failed to fetch data from yfinance for {ticker}: {e}") from e

    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")

    df = _clean_dataframe(df)

    if use_cache:
        cache = Cache()
        cache.set(ticker, df, period, interval)

    return df


def fetch_ohlcv_range(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV data for a date range with configurable interval.

    Caching uses (ticker, range_key, interval) composite key. Range_key
    encodes start_date and end_date to prevent 1h/1d data mixing.
    """
    # Warn about 1h intraday limitation (yfinance typically limits to ~60 days)
    if interval == "1h":
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days_range = (end_dt - start_dt).days
            if days_range > 60:
                logging.warning(
                    "1h intraday requested for %s over %d days. "
                    "yfinance typically only returns ~60 days of 1h data; "
                    "results may be incomplete or empty.",
                    ticker, days_range,
                )
        except ValueError:
            pass  # Date parsing failed; skip length warning

    range_key = f"{start_date}_{end_date}"

    if use_cache:
        cache = Cache()
        cached = cache.get(ticker, range_key, interval)
        if cached is not None:
            return cached

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, interval=interval)
    except Exception as e:
        logging.error(
            "yfinance fetch failed for %s (range %s-%s, interval=%s): %s",
            ticker, start_date, end_date, interval, e,
        )
        raise RuntimeError(f"Failed to fetch data from yfinance for {ticker}: {e}") from e

    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker} in range {start_date} to {end_date}")

    df = _clean_dataframe(df)

    if use_cache:
        cache = Cache()
        cache.set(ticker, df, range_key, interval)

    return df


def fetch_ohlcv_batch(
    tickers: list[str],
    period: str = "2y",
    use_cache: bool = True,
) -> dict[str, pd.DataFrame]:
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = fetch_ohlcv(ticker, period, use_cache)
        except Exception as e:
            print(f"Warning: failed to fetch {ticker}: {e}")
    return results


def get_latest_price(ticker: str) -> Optional[float]:
    cache_key = f"price:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            _cache_set(cache_key, price)
            return price
    except Exception:
        logging.warning("Failed to get latest price for %s", ticker, exc_info=True)
    return None


def get_price_change(ticker: str) -> float:
    """Get daily change percentage for a ticker."""
    cache_key = f"change:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if len(hist) >= 2:
            latest = hist["Close"].iloc[-1]
            previous = hist["Close"].iloc[-2]
            change = round(float((latest - previous) / previous * 100), 2)
            _cache_set(cache_key, change)
            return change
    except Exception:
        logging.warning("Failed to get price change for %s", ticker, exc_info=True)
    return 0.0


def get_company_name(ticker: str) -> str:
    cache_key = f"name:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        stock = yf.Ticker(ticker)
        name = stock.info.get("longName") or stock.info.get("shortName") or ticker
        _cache_set(cache_key, name)
        return name
    except Exception:
        logging.warning("Failed to get company name for %s", ticker, exc_info=True)
        return ticker


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df.columns = [c.lower() for c in df.columns]
    return df
