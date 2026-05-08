import asyncio
from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisRequest, CombinedSignalResponse
from app.services.comparison_service import combine_signals

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.post("/analyze", response_model=CombinedSignalResponse)
async def analyze_comparison(request: AnalysisRequest):
    try:
        result = await asyncio.to_thread(combine_signals, request.ticker, request.timeframe)
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Unable to compare analysis results. Please check the ticker symbol.")
    except Exception:
        raise HTTPException(status_code=500, detail="An internal error occurred during comparison.")
