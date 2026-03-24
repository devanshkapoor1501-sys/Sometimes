"""Feature engineering helpers for technical indicators + sentiment."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _compute_macd(close: pd.Series) -> pd.Series:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    return ema12 - ema26


def engineer_features(df: pd.DataFrame, sentiment_score: float) -> pd.DataFrame:
    data = df.copy()
    data["daily_return"] = data["Close"].pct_change()
    data["ma_5"] = data["Close"].rolling(window=5).mean()
    data["ma_10"] = data["Close"].rolling(window=10).mean()
    data["rsi"] = _compute_rsi(data["Close"])
    data["macd"] = _compute_macd(data["Close"])
    data["volume_change"] = data["Volume"].pct_change()
    data["sentiment_score"] = sentiment_score

    data["target"] = (data["Close"].shift(-1) > data["Close"]).astype(int)
    data = data.dropna().reset_index(drop=True)
    return data


def get_feature_columns() -> list[str]:
    return [
        "daily_return",
        "ma_5",
        "ma_10",
        "rsi",
        "macd",
        "volume_change",
        "sentiment_score",
    ]
