"""Configurable provider layer for stock news headlines."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from app.config import config


def _normalize_item(title: str, source: str, url: str, published_at: str) -> dict[str, str]:
    return {
        "title": title or "Untitled",
        "source": source or "Unknown",
        "url": url or "#",
        "published_at": published_at or "",
    }


def _demo_news(symbol: str) -> list[dict[str, str]]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [
        _normalize_item(
            f"{symbol.upper()} announces new product roadmap",
            "Demo Wire",
            "https://example.com/demo-news-1",
            today,
        ),
        _normalize_item(
            f"Analysts discuss valuation outlook for {symbol.upper()}",
            "Demo Markets",
            "https://example.com/demo-news-2",
            today,
        ),
    ]


def _fetch_newsapi(symbol: str) -> list[dict[str, str]]:
    if not config.newsapi_key:
        raise RuntimeError("NEWSAPI_KEY is missing. Add it to your .env file.")

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": symbol,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": config.newsapi_key,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    articles = payload.get("articles", [])

    return [
        _normalize_item(
            article.get("title", ""),
            (article.get("source") or {}).get("name", "NewsAPI"),
            article.get("url", ""),
            article.get("publishedAt", ""),
        )
        for article in articles
    ]


def _fetch_finnhub(symbol: str) -> list[dict[str, str]]:
    if not config.finnhub_key:
        raise RuntimeError("FINNHUB_KEY is missing. Add it to your .env file.")

    response = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": symbol.upper(),
            "from": datetime.now(timezone.utc).strftime("%Y-%m-01"),
            "to": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "token": config.finnhub_key,
        },
        timeout=15,
    )
    response.raise_for_status()
    items: list[dict[str, Any]] = response.json()

    return [
        _normalize_item(
            item.get("headline", ""),
            item.get("source", "Finnhub"),
            item.get("url", ""),
            str(item.get("datetime", "")),
        )
        for item in items[:10]
    ]


def _fetch_alphavantage(symbol: str) -> list[dict[str, str]]:
    if not config.alphavantage_key:
        raise RuntimeError("ALPHAVANTAGE_KEY is missing. Add it to your .env file.")

    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "NEWS_SENTIMENT",
            "tickers": symbol.upper(),
            "apikey": config.alphavantage_key,
            "limit": 10,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    feed = payload.get("feed", [])

    return [
        _normalize_item(
            item.get("title", ""),
            item.get("source", "Alpha Vantage"),
            item.get("url", ""),
            item.get("time_published", ""),
        )
        for item in feed
    ]


def fetch_news(symbol: str) -> list[dict[str, str]]:
    """Fetch latest news using the selected provider.

    Falls back to demo headlines so the app stays usable without API keys.
    """
    provider = config.news_provider
    try:
        if provider == "newsapi":
            return _fetch_newsapi(symbol)
        if provider == "finnhub":
            return _fetch_finnhub(symbol)
        if provider == "alphavantage":
            return _fetch_alphavantage(symbol)
        return _demo_news(symbol)
    except Exception:
        return _demo_news(symbol)
