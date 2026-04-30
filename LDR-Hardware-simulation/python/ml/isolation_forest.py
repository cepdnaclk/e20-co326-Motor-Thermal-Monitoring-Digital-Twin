"""
Algorithm 2 — Isolation Forest (unsupervised anomaly detection)
Requires no labelled data. Collects WARMUP_NEEDED live readings to establish
a normal baseline, then fits itself. Refits every RETRAIN_EVERY readings to
follow hardware drift. Falls back to hard thresholds during warm-up.

To activate: in edge_ai.py, uncomment
    from ml.isolation_forest import classify, load_model
"""

import joblib
import numpy as np
from pathlib import Path
from collections import deque
from sklearn.ensemble import IsolationForest

from .base import extract_features
from config import T_WARNING, T_CRITICAL

MODEL_PATH    = Path("models/isolation_forest.joblib")
WARMUP_NEEDED = 200    # readings before first fit
RETRAIN_EVERY = 1_000  # readings between periodic refits

_model       : IsolationForest | None = None
_is_fitted   : bool  = False
_thresh_warn : float = 0.0
_thresh_crit : float = 0.0
_buffer      : list  = []   # feature rows accumulated for (re)training
_seen        : int   = 0


def load_model() -> None:
    global _model, _is_fitted, _thresh_warn, _thresh_crit
    if MODEL_PATH.exists():
        saved = joblib.load(MODEL_PATH)
        _model       = saved["model"]
        _thresh_warn = saved["thresh_warn"]
        _thresh_crit = saved["thresh_crit"]
        _is_fitted   = True
        print("[IF   ] Model loaded from disk.")
    else:
        print(f"[IF   ] No saved model — collecting {WARMUP_NEEDED} warm-up readings ...")


def _fit(X: np.ndarray) -> None:
    global _model, _is_fitted, _thresh_warn, _thresh_crit
    _model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    _model.fit(X)
    scores       = _model.decision_function(X)
    _thresh_crit = float(np.percentile(scores, 5))
    _thresh_warn = float(np.percentile(scores, 15))
    _is_fitted   = True
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": _model, "thresh_warn": _thresh_warn, "thresh_crit": _thresh_crit},
        MODEL_PATH,
    )
    print(f"[IF   ] Model fitted (n={len(X)})  warn<{_thresh_warn:.4f}  crit<{_thresh_crit:.4f}")


def _fallback(temperature: float, feat: np.ndarray) -> tuple:
    """Hard-threshold fallback used only during warm-up."""
    z = float(feat[0][1])   # z_score is index 1 in FEATURES
    if temperature > T_CRITICAL:
        return "CRITICAL", -1.0
    if temperature > T_WARNING:
        return "WARNING",  -0.5
    return "NORMAL", z


def classify(temperature: float, window: deque) -> tuple:
    """
    Returns (status, score).
      status : "NORMAL" | "WARNING" | "CRITICAL"
      score  : Isolation Forest decision_function value
               (positive = normal, negative = anomaly)
    """
    global _seen
    feat = extract_features(temperature, window)

    if not _is_fitted:
        _buffer.append(feat[0])
        if len(_buffer) >= WARMUP_NEEDED:
            _fit(np.array(_buffer))
        return _fallback(temperature, feat)

    _seen += 1
    _buffer.append(feat[0])
    if len(_buffer) > 5_000:
        del _buffer[:-5_000]
    if _seen % RETRAIN_EVERY == 0:
        _fit(np.array(_buffer))

    score = float(_model.decision_function(feat)[0])
    if score < _thresh_crit:
        return "CRITICAL", score
    if score < _thresh_warn:
        return "WARNING",  score
    return "NORMAL", score
