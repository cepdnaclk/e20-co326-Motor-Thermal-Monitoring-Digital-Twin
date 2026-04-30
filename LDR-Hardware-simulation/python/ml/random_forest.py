"""
Algorithm 3 — Random Forest classifier
Same synthetic training pipeline as Decision Tree but uses an ensemble of
100 trees for greater robustness. Classification uses per-class probability
thresholds (P_CRITICAL, P_WARNING) instead of a hard argmax, allowing
sensitivity to be tuned without retraining.

To activate: in edge_ai.py, uncomment
    from ml.random_forest import classify, load_model
"""

import joblib
import numpy as np
from pathlib import Path
from collections import deque
from sklearn.ensemble import RandomForestClassifier

from .base import extract_features, generate_training_data

MODEL_PATH = Path("models/random_forest.joblib")
CLASSES    = ["NORMAL", "WARNING", "CRITICAL"]

# Tune these thresholds without retraining to adjust sensitivity
P_CRITICAL: float = 0.50
P_WARNING:  float = 0.40

_model: RandomForestClassifier | None = None


def load_model() -> None:
    global _model
    if MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
        print("[RF   ] Model loaded from disk.")
        return

    print("[RF   ] No saved model — training on synthetic data ...")
    X, y = generate_training_data(n=10_000)
    _model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    _model.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(_model, MODEL_PATH)
    print(f"[RF   ] Model trained and saved to {MODEL_PATH}.")


def classify(temperature: float, window: deque) -> tuple:
    """
    Returns (status, score).
      status : "NORMAL" | "WARNING" | "CRITICAL"
      score  : probability of the returned class (0-1)
    """
    features = extract_features(temperature, window)
    proba    = _model.predict_proba(features)[0]

    p_crit = proba[CLASSES.index("CRITICAL")]
    p_warn = proba[CLASSES.index("WARNING")]

    if p_crit >= P_CRITICAL:
        return "CRITICAL", float(p_crit)
    if p_warn >= P_WARNING:
        return "WARNING",  float(p_warn)
    return "NORMAL", float(proba[CLASSES.index("NORMAL")])
