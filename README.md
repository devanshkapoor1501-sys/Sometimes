# Full-Stack Stock Prediction Web App (Flask + ML + Sentiment)

This project predicts whether a stock is likely to go **UP** or **DOWN** for the next trading day by combining:

1. **Historical market data** from Yahoo Finance (`yfinance`)
2. **News sentiment** from a configurable news provider layer

It includes:
- Flask backend
- HTML/CSS/JavaScript frontend
- Chart.js price chart
- More robust UI with loading-state submit button and responsive cards/tables
- RandomForestClassifier model
- SQLite storage for past predictions
- FinBERT-first sentiment (with VADER fallback)

---

## Project structure

```text
.
├── app
│   ├── __init__.py
│   ├── config.py
│   ├── models
│   │   └── prediction_store.py
│   ├── services
│   │   ├── feature_service.py
│   │   ├── model_service.py
│   │   ├── news_service.py
│   │   ├── sentiment_service.py
│   │   └── stock_service.py
│   ├── static
│   │   ├── css
│   │   │   └── styles.css
│   │   └── js
│   │       └── chart.js
│   ├── templates
│   │   ├── base.html
│   │   ├── history.html
│   │   ├── home.html
│   │   └── results.html
│   └── utils
│       ├── bootstrap.py
│       └── validators.py
├── app.py
├── data
├── .env.example
├── README.md
└── requirements.txt
```

---

## Features implemented

- Search any Yahoo Finance symbol: `AAPL`, `TSLA`, `RELIANCE.NS`, `TCS.NS`, etc.
- Fetch historical OHLCV stock data
- Fetch latest news with provider abstraction (`demo`, `newsapi`, `finnhub`, `alphavantage`)
- Sentiment analysis per headline:
  - Primary: FinBERT (`ProsusAI/finbert`)
  - Fallback: NLTK VADER
- Combined sentiment score (average of headline sentiment values)
- Technical indicators:
  - Daily return
  - 5-day MA
  - 10-day MA
  - RSI
  - MACD
  - Volume change
- Train/test split + model metrics:
  - Accuracy
  - Precision
  - Recall
  - Confusion matrix
- Next-day direction prediction:
  - `Likely UP` if model predicts class 1
  - `Likely DOWN` if model predicts class 0
- Confidence score from classifier probabilities
- Chart for recent close prices
- Save prediction history in SQLite
- Handles failures gracefully; still works with historical-only signals when no live news is available
- Adds heuristic fallback prediction when ML training data is too limited
- Educational disclaimer in UI

---

## Setup instructions

### 1) Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

> Note: `transformers` is optional for FinBERT. If FinBERT cannot load, the app automatically uses VADER fallback.

### 3) Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and insert your API key for whichever provider you select (`NEWS_PROVIDER`).

- For demo mode (no external key), keep:
  - `NEWS_PROVIDER=demo`

### 4) Run the app

```bash
python app.py
```

Open in browser:

- `http://127.0.0.1:5000/` (Home)
- `http://127.0.0.1:5000/history` (Saved predictions)

---

## How prediction logic works (short version)

1. App fetches ~2 years of daily stock data using `yfinance`.
2. App fetches latest headlines through configured provider (or demo fallback).
3. Each headline gets sentiment label + score via FinBERT or VADER fallback.
4. Headlines are combined into one aggregate sentiment score.
5. App computes technical indicators from historical prices and volume.
6. Features = technical indicators + aggregate sentiment score.
7. Label is built as:
   - `1` if next day close > current day close
   - `0` otherwise.
8. Model trains with train/test split using `RandomForestClassifier`.
9. Model predicts next-day direction from latest feature row and outputs probability-based confidence.
10. Result is shown and saved into SQLite.

---

## Notes on API/news fallback behavior

- If provider fails (network/key/limits), service falls back to demo headlines.
- If no news exists, sentiment becomes neutral-ish and prediction still runs using technical features.
- You can swap providers later without changing other app modules.

---

## Disclaimer

This app is for **educational purposes only** and is **not financial advice**.
