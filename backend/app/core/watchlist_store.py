import json
from pathlib import Path

STORE_PATH = Path(__file__).parent.parent.parent / "watchlist.json"


def load_watchlist() -> list[str]:
    if not STORE_PATH.exists():
        save_watchlist([])
        return []
    with open(STORE_PATH) as f:
        return json.load(f)


def save_watchlist(tickers: list[str]):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(tickers, f)