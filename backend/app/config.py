import os
from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DeepSeek / LLM
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"

    # Cache
    CACHE_DIR: Path = Path(__file__).parent.parent / ".cache"
    CACHE_TTL_HOURS: int = 24

    # Thresholds
    TECHNICAL_TRACK_THRESHOLD: float = 0.55
    LLM_TRACK_THRESHOLD: float = 0.52

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Timeframes
    TIMEFRAMES: ClassVar[dict] = {
        "short": {"name": "短線", "days": 5, "description": "1-5 天短線交易"},
        "mid": {"name": "中線", "days": 20, "description": "1-4 週波段操作"},
        "long": {"name": "長線", "days": 60, "description": "1-3 月長線趨勢"},
    }

    model_config = {"env_file": str(Path(__file__).parent.parent / ".env"), "env_file_encoding": "utf-8"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DEEPSEEK_API_KEY:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. "
                "Copy backend/.env.example to backend/.env and fill in your API key "
                "from https://platform.deepseek.com/api_keys"
            )


settings = Settings()
