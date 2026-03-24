"""Startup utilities."""
from __future__ import annotations

import nltk


def ensure_nltk_resources() -> None:
    """Download VADER lexicon if missing."""
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
