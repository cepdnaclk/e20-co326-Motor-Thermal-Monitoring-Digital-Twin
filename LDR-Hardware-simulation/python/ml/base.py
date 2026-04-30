"""
Shared feature engineering used by all supervised ML modules.
Keeps feature definitions consistent so swapping algorithms never
silently changes what the model sees.
"""

import numpy as np
from collections import deque
from config import T_WARNING, T_CRITICAL

FEATURES = ["temperature", "z_score", "delta", "rolling_mean", "rolling_std"]


def extract_features(temperature: float, window: deque) -> np.ndarray:
    """
    Builds a (1, 5) feature matrix from the current reading and rolling window.
    Safe to call with an empty or single-element window.
    """
    arr = np.array(window, dtype=float)

    if len(arr) > 1:
        mean = arr.mean()
        std  = arr.std()
        prev = arr[-1]
    elif len(arr) == 1:
        mean = arr[0]
        std  = 1.0
        prev = arr[0]
    else:
        mean = temperature
        std  = 1.0
        prev = temperature

    z_score = (temperature - mean) / std if std > 0 else 0.0
    delta   = temperature - prev

    return np.array([[temperature, z_score, delta, mean, std]])


def generate_training_data(n: int = 10_000) -> tuple:
    """
    Produces synthetic (X, y) training data labelled by the same threshold
    rules used in the z_score baseline. Shared by Decision Tree and Random
    Forest so both are trained on identical distributions.
    """
    rng = np.random.default_rng(42)

    regimes = [
        (77.0, 3.0,  "NORMAL",   0.70),
        (87.0, 2.0,  "WARNING",  0.20),
        (93.0, 1.5,  "CRITICAL", 0.10),
    ]
    probs = [r[3] for r in regimes]

    X, y = [], []
    # warm up a realistic rolling window
    window_buf = list(rng.normal(77, 3, 50))

    for _ in range(n):
        idx = rng.choice(len(regimes), p=probs)
        mu, sigma, label, _ = regimes[idx]
        temp = float(rng.normal(mu, sigma))

        dq = deque(window_buf[-50:], maxlen=50)
        X.append(extract_features(temp, dq)[0])
        y.append(label)
        window_buf.append(temp)

    return np.array(X), np.array(y)
