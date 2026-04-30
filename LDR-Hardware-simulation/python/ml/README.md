# ML Control Module — Developer Guide

This package contains the plug-and-play classification modules that drive the
fan control decision in the edge AI container. Each module exposes the same
two-function contract so they are fully interchangeable.

---

## How to Switch Algorithms

Open [../edge_ai.py](../edge_ai.py) and find the swap block near the top:

```python
# --- SWAP LINE: uncomment exactly one to choose the active algorithm ---
from ml.z_score          import classify, load_model   # Algo 0 — original baseline (default)
# from ml.decision_tree    import classify, load_model  # Algo 1
# from ml.isolation_forest import classify, load_model  # Algo 2
# from ml.random_forest    import classify, load_model  # Algo 3
```

Comment in exactly one line, then rebuild the container:

```bash
docker-compose up --build python-edge
```

No other files need to change.

---

## Module Contract

Every module must expose these two functions with these exact signatures:

```python
def load_model() -> None:
    """Called once at container startup. Load or train the model here."""

def classify(temperature: float, window: deque) -> tuple[str, float]:
    """
    Args:
        temperature : current sensor reading in °C
        window      : deque of the last 50 readings (oldest first)
    Returns:
        status : "NORMAL" | "WARNING" | "CRITICAL"
        score  : continuous numeric score for logging (replaces z-score in MQTT payload)
    """
```

The fan control logic and MQTT publishing in `edge_ai.py` rely only on these
two functions — nothing else is imported from a module.

---

## File Layout

```
ml/
├── README.md              ← this file
├── __init__.py
├── base.py                ← shared feature engineering (used by Algo 1 & 3)
├── z_score.py             ← Algo 0: original baseline, no training
├── decision_tree.py       ← Algo 1: supervised, trains on synthetic data
├── isolation_forest.py    ← Algo 2: unsupervised, self-trains from live data
└── random_forest.py       ← Algo 3: supervised ensemble, trains on synthetic data

../models/                 ← persisted .joblib files (created at runtime)
    decision_tree.joblib
    isolation_forest.joblib
    random_forest.joblib
```

> The `models/` directory is created automatically. Add it to `.gitignore` —
> model files are large binaries that should not be committed.

---

## Algorithm 0 — Z-Score Baseline (`z_score.py`)

### How it works

Computes the z-score of the current reading relative to a rolling 50-reading
window and classifies using hard absolute thresholds from `config.py`:

```
temperature > T_CRITICAL (90 °C) → CRITICAL
temperature > T_WARNING  (85 °C) → WARNING
otherwise                        → NORMAL
```

The z-score is returned as the `score` field but does **not** influence the
classification — that is purely threshold-driven.

### Training

**None required.** This module has no model to train or load. `load_model()`
is a no-op stub.

### When to use

- Default starting point — identical behaviour to the original system.
- Regression baseline when evaluating other algorithms.
- Fallback if a trained model file is accidentally deleted.

### Adjusting thresholds

Edit `T_WARNING` and `T_CRITICAL` in [../config.py](../config.py). No rebuild
needed if you change them while the module is active — the values are read at
import time, so rebuild the container after changing them.

---

## Algorithm 1 — Decision Tree (`decision_tree.py`)

### How it works

A `DecisionTreeClassifier` (max depth 6) is trained on 10 000 synthetic
samples generated from three Gaussian temperature regimes (NORMAL ≈ 77 °C,
WARNING ≈ 87 °C, CRITICAL ≈ 93 °C). Each sample is labelled using the same
threshold rules as the z_score baseline. The model classifies based on five
features computed by `base.extract_features()`:

| Feature | Description |
|---|---|
| `temperature` | Current reading in °C |
| `z_score` | (temp − window mean) / window std |
| `delta` | temp − previous reading |
| `rolling_mean` | Mean of the last 50 readings |
| `rolling_std` | Std deviation of the last 50 readings |

### Training

**Automatic on first startup.** If `models/decision_tree.joblib` does not
exist, the model is trained when `load_model()` is called (container startup).
Training takes approximately 1 second.

You will see this log line when training runs:

```
[DT   ] No saved model — training on synthetic data ...
[DT   ] Model trained and saved to models/decision_tree.joblib.
```

On subsequent startups the saved model is loaded instead:

```
[DT   ] Model loaded from disk.
```

### Force retrain

Delete the saved file and restart the container:

```bash
rm python/models/decision_tree.joblib
docker-compose up --build python-edge
```

### Tune without retraining

The Decision Tree has no runtime-tunable parameters. To change behaviour,
adjust the training distribution in `base.generate_training_data()` (the
`regimes` list and their `mu`, `sigma`, `prob` values), delete the `.joblib`
file, and let the container retrain.

---

## Algorithm 2 — Isolation Forest (`isolation_forest.py`)

### How it works

An unsupervised anomaly detection model that requires **no labels**. It
collects the first `WARMUP_NEEDED = 200` live sensor readings to establish
a normal baseline, then fits an `IsolationForest(n_estimators=100,
contamination=0.05)`. It automatically refits every `RETRAIN_EVERY = 1000`
readings to follow hardware drift.

The model's `decision_function` score is mapped to classes via two thresholds
computed at fit time from the training data distribution:

```
score < thresh_crit (5th percentile)  → CRITICAL
score < thresh_warn (15th percentile) → WARNING
score ≥ thresh_warn                   → NORMAL
```

Positive scores indicate normal behaviour; negative scores indicate anomalies.

### Training

**Automatic from live data — no offline step needed.**

#### Warm-up period (first ~400 seconds / ~200 readings)

During warm-up the model is not yet fitted. The container uses the z_score
hard-threshold fallback and simultaneously collects feature vectors. You will
see:

```
[IF   ] No saved model — collecting 200 warm-up readings ...
```

Once 200 readings are collected the model fits itself:

```
[IF   ] Model fitted (n=200)  warn<-0.0312  crit<-0.0891
```

#### Periodic refit (every 1 000 readings)

The model silently refits in-place every 1 000 readings using the rolling
feature buffer (capped at 5 000 rows). This keeps thresholds calibrated as
the LDR hardware ages or ambient conditions change.

#### If a saved model exists

On container startup, if `models/isolation_forest.joblib` exists from a
previous run, it is loaded immediately — no warm-up needed:

```
[IF   ] Model loaded from disk.
```

### Force retrain from scratch

Delete the saved file and restart the container:

```bash
rm python/models/isolation_forest.joblib
docker-compose up python-edge
```

The container will go through the warm-up phase again.

### Tune sensitivity

Two constants at the top of `isolation_forest.py` control behaviour:

| Constant | Default | Effect |
|---|---|---|
| `WARMUP_NEEDED` | 200 | Readings before first fit. Increase for a more stable baseline. |
| `RETRAIN_EVERY` | 1000 | Readings between refits. Decrease for faster drift adaptation. |
| `contamination` | 0.05 | Expected anomaly fraction in training data. Increase to make the model more sensitive. |

The class-boundary percentiles (5th and 15th) are recalculated automatically
after each fit — you do not need to set them manually.

---

## Algorithm 3 — Random Forest (`random_forest.py`)

### How it works

A `RandomForestClassifier` (100 trees, max depth 8) trained on the same
10 000 synthetic samples as the Decision Tree. Uses the same five-feature
vector from `base.extract_features()`.

Unlike the Decision Tree, classification uses **per-class probability
thresholds** instead of a hard argmax, giving finer control over sensitivity:

```
P(CRITICAL) ≥ P_CRITICAL (0.50) → CRITICAL
P(WARNING)  ≥ P_WARNING  (0.40) → WARNING
otherwise                        → NORMAL
```

### Training

**Automatic on first startup**, identical to the Decision Tree. Training takes
approximately 3–5 seconds (100 trees, multi-core via `n_jobs=-1`).

Log output:

```
[RF   ] No saved model — training on synthetic data ...
[RF   ] Model trained and saved to models/random_forest.joblib.
```

On subsequent startups:

```
[RF   ] Model loaded from disk.
```

### Force retrain

```bash
rm python/models/random_forest.joblib
docker-compose up --build python-edge
```

### Tune sensitivity without retraining

Edit the two probability thresholds at the top of `random_forest.py`:

```python
P_CRITICAL: float = 0.50   # lower → triggers CRITICAL more easily
P_WARNING:  float = 0.40   # lower → triggers WARNING more easily
```

Save the file and rebuild the container. The model file is **not** deleted —
the same trained model is reloaded with the new thresholds applied.

---

## Adding a New Algorithm

1. Create `ml/your_algo.py` with `load_model()` and `classify()` matching the
   contract above.
2. Add a commented import line to the swap block in `edge_ai.py`:
   ```python
   # from ml.your_algo import classify, load_model  # Algo N
   ```
3. Uncomment it, rebuild, done.

No other files need to change.

---

## Quick Reference

| | Z-Score | Decision Tree | Isolation Forest | Random Forest |
|---|---|---|---|---|
| Training trigger | None | Auto at startup | Auto from live data | Auto at startup |
| Training time | — | ~1 s | ~400 s warm-up | ~3–5 s |
| Persisted file | None | `decision_tree.joblib` | `isolation_forest.joblib` | `random_forest.joblib` |
| Force retrain | N/A | Delete `.joblib` | Delete `.joblib` | Delete `.joblib` |
| Tune without retrain | Edit `config.py` thresholds | Not supported | Edit `WARMUP_NEEDED`, `RETRAIN_EVERY`, `contamination` | Edit `P_CRITICAL`, `P_WARNING` |
| Needs labels | No | No (synthetic) | No | No (synthetic) |
| Adapts to drift | No | No | Yes (periodic refit) | No |
