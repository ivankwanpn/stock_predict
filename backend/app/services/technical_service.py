from app.core.indicators import compute_all_indicators
from app.core.signals import generate_signal, TechnicalSignal
from app.models.schemas import TechnicalSignalResponse
from app.services.data_service import fetch_ohlcv


def analyze_ticker(ticker: str, timeframe: str = "short") -> TechnicalSignalResponse:
    period_map = {
        "short": "6mo",
        "mid": "1y",
        "long": "2y",
    }
    period = period_map.get(timeframe, "6mo")

    df = fetch_ohlcv(ticker, period=period)
    df_with_indicators = compute_all_indicators(df)
    signal = generate_signal(df_with_indicators, ticker=ticker)

    return TechnicalSignalResponse(
        ticker=signal.ticker,
        direction=signal.direction,
        confidence=signal.confidence,
        key_support=signal.key_support,
        key_resistance=signal.key_resistance,
        indicator_details=signal.indicator_details,
        summary=signal.summary,
    )
