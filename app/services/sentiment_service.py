"""Sentiment analysis with FinBERT-first strategy and VADER fallback."""
from __future__ import annotations

from dataclasses import dataclass

from nltk.sentiment import SentimentIntensityAnalyzer


@dataclass
class SentimentItem:
    title: str
    label: str
    score: float


class SentimentAnalyzer:
    """Analyze finance news sentiment.

    Attempts to use FinBERT via transformers pipeline. If unavailable, falls
    back to NLTK VADER for lightweight local inference.
    """

    def __init__(self) -> None:
        self.mode = "vader"
        self._finbert = None
        self._vader = None
        self._initialize()

    def _initialize(self) -> None:
        try:
            from transformers import pipeline

            self._finbert = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
            )
            self.mode = "finbert"
        except Exception:
            self._vader = SentimentIntensityAnalyzer()
            self.mode = "vader"

    def score_headline(self, text: str) -> tuple[str, float]:
        if self.mode == "finbert" and self._finbert is not None:
            result = self._finbert(text[:512])[0]
            label = str(result["label"]).lower()
            conf = float(result["score"])
            if label == "positive":
                return "positive", conf
            if label == "negative":
                return "negative", -conf
            return "neutral", 0.0

        assert self._vader is not None
        compound = self._vader.polarity_scores(text)["compound"]
        if compound >= 0.05:
            return "positive", compound
        if compound <= -0.05:
            return "negative", compound
        return "neutral", compound

    def analyze_news(self, headlines: list[dict[str, str]]) -> tuple[list[SentimentItem], float]:
        if not headlines:
            return [], 0.0

        results: list[SentimentItem] = []
        score_sum = 0.0
        for item in headlines:
            label, score = self.score_headline(item.get("title", ""))
            score_sum += score
            results.append(SentimentItem(title=item.get("title", ""), label=label, score=score))

        aggregate = score_sum / max(len(results), 1)
        return results, float(aggregate)
