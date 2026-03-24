"""Model training and inference logic for stock direction prediction."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.config import config
from app.services.feature_service import get_feature_columns


@dataclass
class ModelOutcome:
    prediction_label: str
    confidence: float
    metrics: dict[str, object]
    model_used: str


def _heuristic_prediction(feature_df: pd.DataFrame) -> ModelOutcome:
    latest_return = float(feature_df["daily_return"].iloc[-1])
    pred = 1 if latest_return >= 0 else 0
    label = "Likely UP" if pred == 1 else "Likely DOWN"
    # A conservative confidence to avoid over-claiming from heuristic logic.
    confidence = 0.55
    return ModelOutcome(
        prediction_label=label,
        confidence=confidence,
        metrics={
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "confusion_matrix": [[0, 0], [0, 0]],
            "note": "Heuristic fallback used due to limited training data.",
        },
        model_used="heuristic_fallback",
    )


def train_and_predict(feature_df: pd.DataFrame) -> ModelOutcome:
    feature_cols = get_feature_columns()

    if len(feature_df) < 30 or feature_df["target"].nunique() < 2:
        return _heuristic_prediction(feature_df)

    x = feature_df[feature_cols]
    y = feature_df["target"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=config.model_random_state,
        shuffle=False,
    )

    if y_train.nunique() < 2:
        return _heuristic_prediction(feature_df)

    model = RandomForestClassifier(n_estimators=250, random_state=config.model_random_state)
    model.fit(x_train, y_train)

    test_preds = model.predict(x_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, test_preds)),
        "precision": float(precision_score(y_test, test_preds, zero_division=0)),
        "recall": float(recall_score(y_test, test_preds, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_test, test_preds).tolist(),
    }

    latest_features = x.iloc[[-1]]
    probs = model.predict_proba(latest_features)[0]
    pred = int(model.predict(latest_features)[0])

    confidence = float(probs[pred])
    label = "Likely UP" if pred == 1 else "Likely DOWN"

    return ModelOutcome(prediction_label=label, confidence=confidence, metrics=metrics, model_used="random_forest")
