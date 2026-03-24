"""Flask entry point for the stock prediction web app."""
from __future__ import annotations

import logging

from flask import Flask, flash, redirect, render_template, request, url_for

from app.config import config
from app.models.prediction_store import fetch_history, init_db, save_prediction
from app.services.feature_service import engineer_features
from app.services.model_service import train_and_predict
from app.services.news_service import fetch_news
from app.services.sentiment_service import SentimentAnalyzer
from app.services.stock_service import fetch_stock_data
from app.utils.bootstrap import ensure_nltk_resources
from app.utils.validators import is_valid_symbol, normalize_symbol

app = Flask(__name__)
app.config["SECRET_KEY"] = config.secret_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

init_db()
ensure_nltk_resources()


@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/predict", methods=["POST"])
def predict():
    symbol = normalize_symbol(request.form.get("symbol", ""))

    if not symbol:
        flash("Please enter a stock symbol.", "error")
        return redirect(url_for("home"))

    if not is_valid_symbol(symbol):
        flash("Invalid symbol format. Example valid symbols: AAPL, TSLA, RELIANCE.NS", "error")
        return redirect(url_for("home"))

    try:
        stock_result = fetch_stock_data(symbol)
        stock_df = stock_result.data

        news = fetch_news(symbol)
        analyzer = SentimentAnalyzer()
        sentiments, sentiment_score = analyzer.analyze_news(news)

        feature_df = engineer_features(stock_df, sentiment_score)
        model_outcome = train_and_predict(feature_df)

        latest_close = float(stock_df["Close"].iloc[-1])
        save_prediction(
            symbol=symbol,
            latest_close=latest_close,
            sentiment_score=sentiment_score,
            prediction_label=model_outcome.prediction_label,
            confidence=model_outcome.confidence,
        )

        recent_prices = stock_df.tail(90)
        chart_labels = [d.strftime("%Y-%m-%d") for d in recent_prices["Date"]]
        chart_values = [round(float(v), 2) for v in recent_prices["Close"]]

        return render_template(
            "results.html",
            symbol=symbol,
            latest_close=latest_close,
            prediction=model_outcome.prediction_label,
            confidence=round(model_outcome.confidence * 100, 2),
            sentiment_score=round(sentiment_score, 4),
            sentiments=sentiments,
            news=news,
            chart_labels=chart_labels,
            chart_values=chart_values,
            metrics=model_outcome.metrics,
            sentiment_mode=analyzer.mode,
            model_used=model_outcome.model_used,
        )
    except Exception as exc:
        logger.exception("Prediction failed for %s", symbol)
        flash(
            "Could not generate a prediction right now. Please try another symbol or retry in a moment.",
            "error",
        )
        flash(f"Technical detail: {exc}", "error")
        return redirect(url_for("home"))


@app.route("/history", methods=["GET"])
def history():
    records = fetch_history(limit=100)
    return render_template("history.html", records=records)


if __name__ == "__main__":
    app.run(debug=True)
