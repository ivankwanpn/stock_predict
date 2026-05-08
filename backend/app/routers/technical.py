import asyncio
from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisRequest, TechnicalSignalResponse
from app.services.technical_service import analyze_ticker

router = APIRouter(prefix="/technical", tags=["technical"])


@router.post("/analyze", response_model=TechnicalSignalResponse)
async def analyze_technical(request: AnalysisRequest):
    try:
        result = await asyncio.to_thread(analyze_ticker, request.ticker, request.timeframe)
        return result
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ticker symbol or no data available.")
    except Exception:
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")
