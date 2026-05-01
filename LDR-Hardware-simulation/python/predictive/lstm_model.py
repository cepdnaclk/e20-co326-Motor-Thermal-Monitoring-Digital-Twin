"""
LSTM inference wrapper for the predictive maintenance service.

Loads a pre-trained .keras model and implements the predict(buf) interface
expected by model_registry.py and predictive_service.py.

The .keras file is trained locally (train_lstm.py) and mounted into the
Docker container via the models/ volume.
"""

from __future__ import annotations

import os
import sys

import numpy as np

from .buffer import SlidingBuffer

# Import T_WARNING from shared config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import T_WARNING

SEQUENCE_LEN = 30          # must match train_lstm.py
READING_INTERVAL_S = 2
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "models", "lstm_motor.keras",
)

_model = None


def _load_model():
    """Lazy-load the keras model on first call."""
    global _model
    if _model is not None:
        return

    import tensorflow as tf

    resolved = os.path.abspath(MODEL_PATH)
    if not os.path.exists(resolved):
        raise FileNotFoundError(
            f"LSTM model not found at {resolved}. "
            "Run train_lstm.py locally first, then mount models/ into the container."
        )
    _model = tf.keras.models.load_model(resolved)
    print(f"[PREDICT] LSTM model loaded from {resolved}")


def _extract_features(readings: list[float]) -> np.ndarray:
    """
    Convert a list of temperature readings to the LSTM input tensor.

    Must produce the EXACT same features as train_lstm.py:create_sequences().
    Returns shape (1, SEQUENCE_LEN, 3).
    """
    arr = np.array(readings, dtype=np.float32)
    mean = arr.mean()
    std = max(float(arr.std()), 1e-6)

    features = []
    for i, temp in enumerate(arr):
        t_norm = temp / 100.0
        z = (temp - mean) / std
        delta = (temp - arr[i - 1]) / 10.0 if i > 0 else 0.0
        features.append([t_norm, z, delta])

    return np.array([features], dtype=np.float32)


def predict(buf: SlidingBuffer) -> dict:
    """
    Predict anomaly risk using the LSTM model.

    Returns:
        {"risk_score": float, "eta_minutes": float|None, "model": "lstm"}
    """
    if len(buf) < SEQUENCE_LEN:
        return {"risk_score": 0.0, "eta_minutes": None, "model": "lstm (warming up)"}

    _load_model()

    readings = buf.latest(SEQUENCE_LEN)
    features = _extract_features(readings)
    risk_score = float(_model.predict(features, verbose=0)[0][0])

    # Estimate ETA using slope when risk is elevated
    current_temp = readings[-1]
    eta_minutes = None
    if risk_score > 0.3 and current_temp < T_WARNING:
        slope = (readings[-1] - readings[0]) / len(readings)
        if slope > 0:
            readings_needed = (T_WARNING - current_temp) / slope
            eta_minutes = round((readings_needed * READING_INTERVAL_S) / 60.0, 2)
            if eta_minutes > 60.0:
                eta_minutes = None

    return {
        "risk_score": round(risk_score, 4),
        "eta_minutes": eta_minutes,
        "model": "lstm",
    }
