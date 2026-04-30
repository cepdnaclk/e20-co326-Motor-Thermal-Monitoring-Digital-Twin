"""
Algorithm 1 — Decision Tree classifier
Trained on synthetic data generated from the same threshold rules as the
z_score baseline. If a persisted model exists it is loaded; otherwise the
model is trained at container startup (takes ~1 s).

To activate: in edge_ai.py, uncomment
    from ml.decision_tree import classify, load_model
"""

import joblib
import numpy as np
from pathlib import Path
from collections import deque
from sklearn.tree import DecisionTreeClassifier

from .base import extract_features, generate_training_data

MODEL_PATH = Path("models/decision_tree.joblib")
CLASSES    = ["NORMAL", "WARNING", "CRITICAL"]

_model: DecisionTreeClassifier | None = None


def load_model() -> None:
    global _model
    if MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
        print("[DT   ] Model loaded from disk.")
        return

    print("[DT   ] No saved model — training on synthetic data ...")
    X, y = generate_training_data(n=10_000)
    _model = DecisionTreeClassifier(
        max_depth=6,
        class_weight="balanced",
        random_state=42,
    )
    _model.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(_model, MODEL_PATH)
    print(f"[DT   ] Model trained and saved to {MODEL_PATH}.")


def classify(temperature: float, window: deque) -> tuple:
    """
    Returns (status, score).
      status : "NORMAL" | "WARNING" | "CRITICAL"
      score  : model confidence in the predicted class (0-1)
    """
    features = extract_features(temperature, window)
    label    = _model.predict(features)[0]
    proba    = _model.predict_proba(features)[0]
    score    = float(proba[CLASSES.index(label)])
    return label, score
