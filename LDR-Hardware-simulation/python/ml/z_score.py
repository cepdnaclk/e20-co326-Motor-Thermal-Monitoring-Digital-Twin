"""
Algorithm 0 — Z-Score Baseline
Exact logic extracted from the original edge_ai.py classify() function.
Uses a rolling-window z-score for reporting and hard absolute thresholds
(T_WARNING, T_CRITICAL from config) for the control decision.
"""

import numpy as np
from collections import deque
from config import T_WARNING, T_CRITICAL

MIN_READINGS = 10


def load_model():
    """No-op — satisfies the module contract so edge_ai.py can call it unconditionally."""
    pass


def classify(temperature: float, window: deque) -> tuple:
    """
    Returns (status, score).
      status : "NORMAL" | "WARNING" | "CRITICAL"
      score  : z-score of the current reading relative to the rolling window
    """
    z = 0.0
    if len(window) >= MIN_READINGS:
        arr = np.array(window)
        mean, std = arr.mean(), arr.std()
        if std > 0:
            z = (temperature - mean) / std

    if temperature > T_CRITICAL:
        return "CRITICAL", z
    if temperature > T_WARNING:
        return "WARNING", z
    return "NORMAL", z
