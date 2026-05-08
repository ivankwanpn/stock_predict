import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalysisRequest, LLMSignalResponse
from app.services.llm_service import analyze_ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])

LLM_TIMEOUT_SECONDS = 290


@router.post("/analyze", response_model=LLMSignalResponse)
async def analyze_llm(request: AnalysisRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(analyze_ticker, request.ticker, request.timeframe),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("LLM analysis timed out for ticker %s", request.ticker)
        raise HTTPException(status_code=504, detail="Analysis timed out. Please try again later.")
    except ValueError as e:
        logger.warning("LLM analysis ValueError for ticker %s: %s", request.ticker, e)
        raise HTTPException(status_code=404, detail="Invalid ticker symbol or no data available.")
    except Exception as e:
        logger.exception("LLM analysis failed for ticker %s", request.ticker)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")
