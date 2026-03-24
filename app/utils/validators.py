"""Validation helpers for request inputs."""
from __future__ import annotations

import re

# Supports symbols like AAPL, TSLA, RELIANCE.NS, TCS.NS, BRK-B
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")


def normalize_symbol(raw_symbol: str) -> str:
    return raw_symbol.strip().upper()


def is_valid_symbol(symbol: str) -> bool:
    return bool(SYMBOL_PATTERN.match(symbol))
