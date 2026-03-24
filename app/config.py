"""Central configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Runtime configuration values."""

    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    database_path: str = os.getenv("DATABASE_PATH", "data/predictions.db")
    news_provider: str = os.getenv("NEWS_PROVIDER", "demo").lower()
    newsapi_key: str = os.getenv("NEWSAPI_KEY", "")
    finnhub_key: str = os.getenv("FINNHUB_KEY", "")
    alphavantage_key: str = os.getenv("ALPHAVANTAGE_KEY", "")
    model_random_state: int = int(os.getenv("MODEL_RANDOM_STATE", "42"))


config = Config()
