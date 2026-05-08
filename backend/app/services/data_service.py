import pandas as pd

from app.core.data_fetcher import fetch_ohlcv as _fetch_ohlcv
from app.core.data_fetcher import fetch_ohlcv_range as _fetch_ohlcv_range
from app.core.data_fetcher import get_company_name as _get_company_name
from app.core.data_fetcher import fetch_ohlcv_batch as _fetch_ohlcv_batch
from app.core.data_fetcher import get_latest_price as _get_latest_price
from app.core.data_fetcher import get_price_change as _get_price_change
from app.core.indicators import compute_all_indicators as _compute_all_indicators
from app.core.indicators import get_price_summary as _get_price_summary
from app.core.indicators import get_indicators_with_descriptions as _get_indicators_with_descriptions
from app.core.signals import generate_signal as _generate_signal
from app.core.cache import Cache


def fetch_ohlcv(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    return _fetch_ohlcv(ticker, period=period, interval=interval)


def get_ohlcv_range(ticker: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    return _fetch_ohlcv_range(ticker, start_date, end_date, interval)


def get_company_name(ticker: str) -> str:
    return _get_company_name(ticker)


def fetch_ohlcv_batch(tickers: list[str]) -> dict[str, pd.DataFrame]:
    return _fetch_ohlcv_batch(tickers)


def invalidate_cache(ticker: str) -> None:
    cache = Cache()
    cache.invalidate(ticker)


def clear_cache() -> None:
    cache = Cache()
    cache.clear()


def get_latest_price(ticker: str):
    return _get_latest_price(ticker)


def get_price_change(ticker: str) -> float:
    return _get_price_change(ticker)


def compute_all_indicators(df):
    return _compute_all_indicators(df)


def generate_signal(df, ticker: str = ""):
    return _generate_signal(df, ticker)


def get_price_summary(df):
    return _get_price_summary(df)


def get_indicators_with_descriptions(df):
    return _get_indicators_with_descriptions(df)
