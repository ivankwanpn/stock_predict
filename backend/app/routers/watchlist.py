import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.services.data_service import get_latest_price, get_company_name, get_price_change
from app.core.watchlist_store import load_watchlist, save_watchlist
from app.models.schemas import (
    WatchlistItemResponse,
    WatchlistAddRequest,
    WatchlistRemoveRequest,
    StockSearchResult,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


async def _fetch_watchlist_item(ticker: str) -> WatchlistItemResponse:
    price_task = asyncio.to_thread(get_latest_price, ticker)
    name_task = asyncio.to_thread(get_company_name, ticker)
    change_task = asyncio.to_thread(get_price_change, ticker)
    price, name, change_pct = await asyncio.gather(price_task, name_task, change_task)
    if price is not None:
        return WatchlistItemResponse(
            ticker=ticker,
            name=name,
            latest_price=price,
            change_pct=change_pct,
        )
    else:
        return WatchlistItemResponse(
            ticker=ticker,
            name=name,
            latest_price=0.0,
            change_pct=0.0,
        )


@router.get("", response_model=list[WatchlistItemResponse])
async def get_watchlist():
    tickers = load_watchlist()
    items = await asyncio.gather(*[_fetch_watchlist_item(t) for t in tickers])
    return list(items)





@router.post("/add", response_model=list[WatchlistItemResponse])
async def add_to_watchlist(request: WatchlistAddRequest):
    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    tickers = load_watchlist()
    if ticker in tickers:
        raise HTTPException(status_code=400, detail=f"{ticker} is already in watchlist")

    tickers.append(ticker)
    save_watchlist(tickers)

    # Return full updated watchlist with live prices
    items = await asyncio.gather(*[_fetch_watchlist_item(t) for t in tickers])
    return list(items)


@router.post("/remove", response_model=list[WatchlistItemResponse])
async def remove_from_watchlist(request: WatchlistRemoveRequest):
    ticker = request.ticker.strip().upper()
    tickers = load_watchlist()
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f"{ticker} not found in watchlist")

    tickers = [t for t in tickers if t != ticker]
    save_watchlist(tickers)

    # Return full updated watchlist with live prices
    items = await asyncio.gather(*[_fetch_watchlist_item(t) for t in tickers])
    return list(items)


@router.get("/search", response_model=list[StockSearchResult])
async def search_stocks(q: str = Query(..., min_length=1, description="Search query")):
    """Search for stocks by ticker or company name using yfinance."""
    try:
        import yfinance as yf

        results = []

        # Try yfinance Search API (available in yfinance >= 0.2.31)
        try:
            search = yf.Search(q)
            quotes = search.quotes if hasattr(search, "quotes") else []
            for quote in quotes:
                ticker = quote.get("symbol", "")
                name = quote.get("shortname") or quote.get("longname") or ""
                exchange = quote.get("exchange", "")
                market = "HK" if exchange and "HK" in exchange.upper() else "US"

                if ticker and name:
                    results.append(StockSearchResult(ticker=ticker, name=name, market=market))
        except (AttributeError, TypeError):
            # yf.Search not available; fall back to individual lookup
            pass

        # If yfinance Search returned no results, try direct ticker lookup
        if not results:
            # Try as a direct ticker
            try:
                stock = yf.Ticker(q)
                info = stock.info if stock.info else {}
                name = info.get("longName") or info.get("shortName") or q
                exchange = info.get("exchange", "")
                market = "HK" if "HK" in exchange.upper() else "US"
                results.append(StockSearchResult(ticker=q.upper(), name=name, market=market))
            except Exception:
                pass

            # Also try common HK suffix and US patterns
            for suffix in [".HK"]:
                alt_ticker = q.upper() + suffix if not q.upper().endswith(suffix) else q.upper()
                try:
                    stock = yf.Ticker(alt_ticker)
                    info = stock.info if stock.info else {}
                    if info and info.get("regularMarketPrice") is not None:
                        name = info.get("longName") or info.get("shortName") or alt_ticker
                        results.append(StockSearchResult(ticker=alt_ticker, name=name, market="HK"))
                        break
                except Exception:
                    continue

        return results

    except ImportError:
        raise HTTPException(status_code=500, detail="Search service is currently unavailable.")
