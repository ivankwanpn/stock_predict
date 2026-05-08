import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from app.config import settings


class Cache:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = settings.CACHE_DIR / "ohlcv_cache.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_cache (
                    ticker TEXT NOT NULL,
                    period TEXT NOT NULL DEFAULT '2y',
                    interval TEXT NOT NULL DEFAULT '1d',
                    fetched_at TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (ticker, period, interval)
                )
            """)

    def get(self, ticker: str, period: str = "2y", interval: str = "1d") -> Optional[pd.DataFrame]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT fetched_at, data_json FROM ohlcv_cache WHERE ticker = ? AND period = ? AND interval = ?",
                (ticker, period, interval),
            ).fetchone()

        if row is None:
            return None

        fetched_at = datetime.fromisoformat(row[0])
        if datetime.now() - fetched_at > timedelta(hours=settings.CACHE_TTL_HOURS):
            return None

        data = json.loads(row[1])
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        return df

    def set(self, ticker: str, df: pd.DataFrame, period: str = "2y", interval: str = "1d"):
        df_copy = df.copy()
        if df_copy.index.name == "date":
            df_copy = df_copy.reset_index()
        data_json = df_copy.to_json(orient="records", date_format="iso")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ohlcv_cache (ticker, period, interval, fetched_at, data_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ticker, period, interval, datetime.now().isoformat(), data_json),
            )
            conn.commit()

    def invalidate(self, ticker: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM ohlcv_cache WHERE ticker = ?", (ticker,))
            conn.commit()

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM ohlcv_cache")
            conn.commit()
