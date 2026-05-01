"""
Feature engineering helpers shared by all predictive models.

All functions operate on plain numpy arrays or lists of floats,
so they can be unit-tested without MQTT or Docker.
"""

import numpy as np


def extract_slope(readings: np.ndarray) -> float:
    """
    Compute the linear slope (°C per reading) of a 1-D array of
    temperature values using least-squares regression.

    Returns 0.0 if fewer than 2 readings are provided.
    """
    n = len(readings)
    if n < 2:
        return 0.0

    # x = [0, 1, 2, ..., n-1]
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = readings.mean()

    numerator = np.sum((x - x_mean) * (readings - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return 0.0

    return float(numerator / denominator)


def extract_rolling_stats(readings: np.ndarray) -> dict:
    """
    Compute basic rolling statistics used for LSTM feature vectors.

    Returns a dict with keys: mean, std, min, max, delta
    """
    if len(readings) == 0:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "delta": 0.0}

    return {
        "mean": float(np.mean(readings)),
        "std": float(np.std(readings)) if len(readings) > 1 else 0.0,
        "min": float(np.min(readings)),
        "max": float(np.max(readings)),
        "delta": float(readings[-1] - readings[0]) if len(readings) > 1 else 0.0,
    }
