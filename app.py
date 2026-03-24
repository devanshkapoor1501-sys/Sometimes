"""
Beginner-friendly Flask stock prediction app.

What it does:
1) Takes a stock symbol from the user (like AAPL or TSLA)
2) Downloads historical price data with yfinance
3) Fetches related news headlines (NewsAPI if key exists, otherwise demo headlines)
4) Runs VADER sentiment on headlines
5) Builds simple features (moving averages + price change)
6) Trains a small model (RandomForest) and predicts next-day direction
7) Shows result, confidence, sentiment, chart, and headlines
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import plotly
import plotly.graph_objs as go
import requests
from flask import Flask, render_template, request
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yfinance as yf

app = Flask(__name__)


# --------------------------
# Data + feature functions
# --------------------------
def fetch_stock_data(symbol: str, period: str = "2y") -> pd.DataFrame:
    """Download historical daily stock data from Yahoo Finance."""
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError("No stock data found. Check the ticker symbol and try again.")

    df = df.reset_index()
    # Keep only columns we use to keep things simple for students.
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Create easy technical indicators.

    Features:
    - price_change: daily % change
    - ma_5: 5-day moving average
    - ma_10: 10-day moving average
    """
    data = df.copy()
    data["price_change"] = data["Close"].pct_change()
    data["ma_5"] = data["Close"].rolling(5).mean()
    data["ma_10"] = data["Close"].rolling(10).mean()

    # Label: 1 if next day close is higher than today, else 0
    data["target"] = (data["Close"].shift(-1) > data["Close"]).astype(int)
    data = data.dropna().reset_index(drop=True)
    return data


# --------------------------
# News + sentiment functions
# --------------------------
def fetch_news(symbol: str) -> list[dict[str, str]]:
    """Fetch latest headlines.

    Uses NewsAPI if NEWSAPI_KEY is available.
    Falls back to simple demo headlines if not.
    """
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return [
            {
                "title": f"{symbol.upper()} sees steady investor interest",
                "source": "Demo News",
                "publishedAt": today,
                "url": "https://example.com/demo1",
            },
            {
                "title": f"Analysts discuss {symbol.upper()} growth outlook",
                "source": "Demo News",
                "publishedAt": today,
                "url": "https://example.com/demo2",
            },
        ]

    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=10)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": symbol,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 8,
        "apiKey": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])
        return articles[:8]
    except Exception:
        # Safe fallback so app still runs.
        return []


def analyze_sentiment(headlines: list[dict[str, str]]) -> tuple[list[dict[str, str | float]], float]:
    """Analyze headline sentiment using VADER.

    Returns:
    - per-headline sentiment labels + scores
    - one combined sentiment score (average compound)
    """
    analyzer = SentimentIntensityAnalyzer()

    if not headlines:
        return [], 0.0

    results = []
    score_sum = 0.0

    for item in headlines:
        title = item.get("title", "")
        compound = analyzer.polarity_scores(title)["compound"]

        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"

        score_sum += compound
        results.append(
            {
                "title": title,
                "label": label,
                "score": round(compound, 4),
                "source": (item.get("source") or {}).get("name", item.get("source", "Unknown")),
                "url": item.get("url", "#"),
            }
        )

    avg_sentiment = score_sum / len(results)
    return results, float(avg_sentiment)


# --------------------------
# Model function
# --------------------------
def predict_direction(feature_df: pd.DataFrame, sentiment_score: float) -> dict[str, float | str]:
    """Train a simple RandomForest model and predict Up/Down for next day."""
    data = feature_df.copy()
    data["sentiment_score"] = sentiment_score

    features = ["price_change", "ma_5", "ma_10", "sentiment_score"]
    x = data[features]
    y = data["target"]

    # If very small data or one-class labels, use a tiny fallback rule.
    if len(data) < 25 or y.nunique() < 2:
        pred = 1 if float(data["price_change"].iloc[-1]) >= 0 else 0
        confidence = 0.55
    else:
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, shuffle=False)
        model = RandomForestClassifier(n_estimators=120, random_state=42)
        model.fit(x_train, y_train)

        latest_row = x.iloc[[-1]]
        pred = int(model.predict(latest_row)[0])
        confidence = float(model.predict_proba(latest_row)[0][pred])

    label = "Up" if pred == 1 else "Down"
    return {"prediction": label, "confidence": round(confidence * 100, 2)}


def create_price_chart(df: pd.DataFrame) -> str:
    """Create a Plotly line chart and return JSON for frontend rendering."""
    fig = go.Figure(
        data=[go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Close Price")]
    )
    fig.update_layout(
        title="Recent Closing Prices",
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_white",
        height=420,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return plotly.io.to_json(fig)


# --------------------------
# Flask routes
# --------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    symbol = request.form.get("symbol", "").strip().upper()

    if not symbol:
        return render_template("index.html", error="Please enter a stock symbol.")

    try:
        stock_df = fetch_stock_data(symbol)
        feature_df = add_indicators(stock_df)

        headlines = fetch_news(symbol)
        sentiment_rows, avg_sentiment = analyze_sentiment(headlines)

        pred_result = predict_direction(feature_df, avg_sentiment)

        latest_close = round(float(stock_df["Close"].iloc[-1]), 2)
        chart_json = create_price_chart(stock_df.tail(120))

        return render_template(
            "result.html",
            symbol=symbol,
            latest_close=latest_close,
            prediction=pred_result["prediction"],
            confidence=pred_result["confidence"],
            sentiment_score=round(avg_sentiment, 4),
            sentiment_rows=sentiment_rows,
            headlines=headlines,
            chart_json=chart_json,
        )
    except Exception as exc:
        return render_template("index.html", error=f"Error: {exc}")


if __name__ == "__main__":
    # Run with: python app.py
    app.run(debug=True)
