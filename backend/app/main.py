from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import stock, technical, llm, comparison, watchlist

app = FastAPI(title="Stock Predict API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock.router, prefix="/api")
app.include_router(technical.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(comparison.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
