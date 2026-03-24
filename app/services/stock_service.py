"""Service helpers for downloading stock market data."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf


@dataclass
class StockFetchResult:
    symbol: str
    data: pd.DataFrame


def fetch_stock_data(symbol: str, period: str = "2y", interval: str = "1d") -> StockFetchResult:
    """Fetch historical stock data using yfinance.

    Supports US symbols (AAPL) and Indian symbols (RELIANCE.NS) as long as
    Yahoo Finance provides the ticker.
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval, auto_adjust=False)
    except Exception as exc:
        raise ValueError(f"Failed to fetch market data for {symbol}: {exc}") from exc

    if history.empty:
        raise ValueError(f"No market data returned for symbol: {symbol}")

    history = history.reset_index()
    if "Date" not in history.columns and "Datetime" in history.columns:
        history.rename(columns={"Datetime": "Date"}, inplace=True)

    if "Date" in history.columns:
        history["Date"] = pd.to_datetime(history["Date"]).dt.tz_localize(None)

    required_cols = {"Date", "Close", "Volume"}
    missing = required_cols.difference(history.columns)
    if missing:
        raise ValueError(f"Missing expected market columns: {sorted(missing)}")

    return StockFetchResult(symbol=symbol.upper(), data=history)
