"""SQLite integration for saving and reading stock predictions."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.config import config


def _ensure_dir_exists() -> None:
    db_path = Path(config.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    _ensure_dir_exists()
    conn = sqlite3.connect(config.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                latest_close REAL NOT NULL,
                sentiment_score REAL NOT NULL,
                prediction_label TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_prediction(symbol: str, latest_close: float, sentiment_score: float, prediction_label: str, confidence: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO predictions (symbol, latest_close, sentiment_score, prediction_label, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (symbol, latest_close, sentiment_score, prediction_label, confidence, datetime.utcnow().isoformat()),
        )
        conn.commit()


def fetch_history(limit: int = 50) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, symbol, latest_close, sentiment_score, prediction_label, confidence, created_at
            FROM predictions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows
