# Beginner-Friendly Stock Prediction App (Flask)

This project predicts whether a stock is likely to go **Up** or **Down** by combining:
- historical stock prices from Yahoo Finance
- simple technical indicators
- latest news sentiment

## Files you asked for

- `app.py`
- `templates/index.html`
- `templates/result.html`
- `static/style.css`
- `requirements.txt`

## How it works (simple)

1. User enters a stock ticker (example: `AAPL`, `TSLA`, `RELIANCE.NS`).
2. App downloads historical stock data using `yfinance`.
3. App computes simple indicators:
   - Daily price change
   - 5-day moving average
   - 10-day moving average
4. App fetches stock news headlines (NewsAPI if key is set).
5. App scores headline sentiment with VADER.
6. App trains a small `RandomForestClassifier`.
7. App predicts **Up** or **Down** and shows confidence.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Optional news API key

Set a NewsAPI key if you want live news:

```bash
export NEWSAPI_KEY="your_key_here"  # macOS/Linux
# set NEWSAPI_KEY=your_key_here      # Windows CMD
```

If no key is provided, app uses demo headlines so it still runs.

## Run

```bash
python app.py
```

Open: `http://127.0.0.1:5000/`

## Disclaimer

Educational project only. Not financial advice.
