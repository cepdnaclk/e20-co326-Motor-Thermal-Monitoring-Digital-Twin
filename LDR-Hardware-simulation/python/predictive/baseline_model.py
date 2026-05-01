"""
Phase 1 — Baseline Predictive Model (Linear Slope Extrapolation).

Uses least-squares regression on the most recent readings to estimate
how quickly temperature is rising and when it will cross T_WARNING.

No training required — this model works immediately on live data.
"""

from __future__ import annotations

import numpy as np

from .buffer import SlidingBuffer
from .features import extract_slope

# Import threshold from shared config so it stays in sync with edge_ai
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import T_WARNING

MAX_SLOPE = 1.5            # °C/reading that maps to risk_score = 1.0
READING_INTERVAL_S = 2     # ESP32 / simulator publishes every 2 seconds
SLOPE_WINDOW = 15          # use last 15 readings (30 seconds) for slope


def predict(buf: SlidingBuffer) -> dict:
    """
    Predict anomaly risk from the current buffer contents.

    Returns:
        {
            "risk_score": float,       # 0.0 (safe) to 1.0 (imminent anomaly)
            "eta_minutes": float|None, # estimated minutes until T_WARNING; None if not rising
            "model": "baseline"
        }
    """
    if len(buf) < 5:
        return {"risk_score": 0.0, "eta_minutes": None, "model": "baseline"}

    # Use at most SLOPE_WINDOW readings for slope estimation
    n = min(SLOPE_WINDOW, len(buf))
    readings = np.array(buf.latest(n))
    slope = extract_slope(readings)
    current = readings[-1]

    # Only predict risk when temperature is actively rising
    eta_minutes = None
    if slope > 0 and current < T_WARNING:
        readings_needed = (T_WARNING - current) / slope
        eta_minutes = round((readings_needed * READING_INTERVAL_S) / 60.0, 2)
        # Cap at a reasonable maximum (60 minutes)
        if eta_minutes > 60.0:
            eta_minutes = None   # too far away to be meaningful

    # Normalise slope to a 0–1 risk score
    risk_score = float(np.clip(slope / MAX_SLOPE, 0.0, 1.0))

    return {
        "risk_score": round(risk_score, 4),
        "eta_minutes": eta_minutes,
        "model": "baseline",
    }
