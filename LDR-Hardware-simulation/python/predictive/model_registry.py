"""
Model registry — selects the active predictive model via environment variable.

Set PREDICTIVE_MODEL env var to switch models:
  - "baseline"  (default) — linear slope extrapolation, no training needed
  - "lstm"      — LSTM sequence model, requires trained weights in models/

Usage in predictive_service.py:
    from predictive.model_registry import get_predictor
    predictor = get_predictor()
    result = predictor(buf)
"""

import os


ACTIVE_MODEL = os.getenv("PREDICTIVE_MODEL", "baseline")


def get_predictor():
    """
    Return the predict() function for the active model.

    The returned callable has signature:
        predict(buf: SlidingBuffer) -> dict
    """
    if ACTIVE_MODEL == "lstm":
        from .lstm_model import predict
    else:
        from .baseline_model import predict

    print(f"[PREDICT] Loaded model: {ACTIVE_MODEL}")
    return predict
