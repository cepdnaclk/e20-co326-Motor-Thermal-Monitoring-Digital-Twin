# ML Control Module Plan — Motor Thermal Digital Twin

## Context

The current edge AI module (`python/edge_ai.py`) uses a **Z-score over a rolling 50-reading window** plus hard thresholds (85 °C → WARNING, 90 °C → CRITICAL) to classify each reading and drive fan control. The goal of this document is to replace that classification logic with classical ML algorithms while keeping everything else — MQTT wiring, fan hysteresis, Node-RED dashboard, cloud forwarding — completely untouched.

---

## Plug-and-Play Architecture

All three algorithms slot into a single seam: the `classify()` function and its surrounding model-load block. The rest of `edge_ai.py` never changes.

### Contract

Every ML module must expose one function:

```python
def classify(temperature: float, window: deque) -> tuple[str, float]:
    """
    Returns (status, score).
      status : "NORMAL" | "WARNING" | "CRITICAL"
      score  : continuous anomaly/confidence score for logging (replaces z-score)
    """
```

### Proposed file layout

```
python/
├── edge_ai.py            ← orchestrator, unchanged except 3-line swap
├── config.py             ← unchanged
├── ml/
│   ├── __init__.py
│   ├── base.py           ← shared feature-engineering helpers
│   ├── decision_tree.py  ← Algorithm 1
│   ├── isolation_forest.py  ← Algorithm 2
│   └── random_forest.py  ← Algorithm 3
└── models/               ← persisted .joblib files (git-ignored)
```

### Swap in `edge_ai.py`

```python
# --- SWAP LINE: pick one ---
from ml.decision_tree    import classify, load_model   # Algo 1
# from ml.isolation_forest import classify, load_model  # Algo 2
# from ml.random_forest    import classify, load_model  # Algo 3

# At startup (before MQTT init):
load_model()

# Inside on_message() — unchanged call:
status, score = classify(temperature, window)
```

That single commented-in/out import is the only change needed to switch algorithms.

---

## Shared Feature Engineering (`ml/base.py`)

All supervised models use the same feature vector. Centralising it prevents drift.

```python
import numpy as np
from collections import deque

FEATURES = ["temperature", "z_score", "delta", "rolling_mean", "rolling_std"]

def extract_features(temperature: float, window: deque) -> np.ndarray:
    arr = np.array(window, dtype=float)
    mean = arr.mean() if len(arr) > 0 else temperature
    std  = arr.std()  if len(arr) > 1 else 1.0
    prev = arr[-1]    if len(arr) > 0 else temperature

    z_score = (temperature - mean) / std if std > 0 else 0.0
    delta   = temperature - prev

    return np.array([[temperature, z_score, delta, mean, std]])

def threshold_label(temperature: float, z_score: float) -> str:
    """Generates synthetic labels from the existing rule set for offline training."""
    if temperature >= 90.0:
        return "CRITICAL"
    if temperature >= 85.0 or abs(z_score) > 2.5:
        return "WARNING"
    return "NORMAL"
```

---

## Algorithm 1 — Decision Tree

### Applicability Assessment

| Factor | Assessment |
|--------|-----------|
| Problem type | Multi-class classification (3 classes) — **good fit** |
| Feature space | Low-dimensional (5 features) — **ideal for DT** |
| Inference cost | Single tree traversal, microseconds — **edge-ready** |
| Interpretability | Full if-else tree printable — **debuggable on hardware** |
| Labelled data | Not collected yet — **solved with synthetic generation** |
| Concept drift | Fixed tree won't adapt post-deploy — **manageable with periodic retrain** |

**Verdict: fully applicable.** A Decision Tree can replicate and improve on the threshold logic because it can learn non-linear boundaries across multiple features simultaneously (e.g., a high delta combined with a moderate temperature is more dangerous than the same temperature alone).

### How It Works

A Decision Tree recursively splits the feature space by asking binary questions (`z_score > 1.8?`, `delta > 3.2?`) to minimise class impurity (Gini). The result is an explicit rule tree that maps feature vectors to labels.

### Training Strategy

Because no labelled field data exists yet, training uses **synthetic data generated from the existing rules**:

1. Simulate 10 000 temperature readings drawn from three regimes:
   - NORMAL: Gaussian around 77 °C, σ = 3
   - WARNING: Gaussian around 87 °C, σ = 2
   - CRITICAL: Gaussian around 93 °C, σ = 1.5
2. Build a 50-reading sliding window for each sample to compute all five features.
3. Label each sample using `threshold_label()` from `base.py`.
4. Train `sklearn.tree.DecisionTreeClassifier` with `max_depth=6`, `class_weight="balanced"`.
5. Persist model with `joblib.dump`.

This is done **once offline** (or in a `train.py` script that runs at container startup if no saved model exists).

### Implementation Plan

**New file: `python/ml/decision_tree.py`**

```python
import joblib, numpy as np
from pathlib import Path
from sklearn.tree import DecisionTreeClassifier
from .base import extract_features, threshold_label, FEATURES

MODEL_PATH = Path("models/decision_tree.joblib")
CLASSES    = ["NORMAL", "WARNING", "CRITICAL"]
_model     = None

def _generate_training_data(n=10_000):
    X, y = [], []
    rng = np.random.default_rng(42)
    regimes = [
        (77.0, 3.0,  "NORMAL",   0.7),
        (87.0, 2.0,  "WARNING",  0.2),
        (93.0, 1.5,  "CRITICAL", 0.1),
    ]
    window = list(rng.normal(77, 3, 50))
    for _ in range(n):
        label_target, _, label_str, _ = rng.choice(regimes, p=[0.7, 0.2, 0.1])
        # pick regime
        idx = rng.choice(3, p=[0.7, 0.2, 0.1])
        mu, sigma, label_str, _ = regimes[idx]
        temp = float(rng.normal(mu, sigma))
        from collections import deque
        dq = deque(window[-50:], maxlen=50)
        feat = extract_features(temp, dq)
        X.append(feat[0])
        y.append(label_str)
        window.append(temp)
    return np.array(X), np.array(y)

def load_model():
    global _model
    if MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
        return
    X, y = _generate_training_data()
    _model = DecisionTreeClassifier(max_depth=6, class_weight="balanced", random_state=42)
    _model.fit(X, y)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(_model, MODEL_PATH)

def classify(temperature, window):
    features = extract_features(temperature, window)
    label    = _model.predict(features)[0]
    proba    = _model.predict_proba(features)[0]
    score    = float(proba[CLASSES.index(label)])   # confidence as score
    return label, score
```

**Modified lines in `edge_ai.py`** (3 lines total):
```python
# line ~5:  add import
from ml.decision_tree import classify, load_model

# line ~27: add after globals
load_model()

# line ~58: replace classify(temperature) call
status, score = classify(temperature, window)
```

### Pros / Cons

| Pros | Cons |
|------|------|
| Human-readable tree — can be printed and validated | Fixed after training; won't adapt to hardware drift without retrain |
| Very fast inference | Synthetic training data may not cover all real edge cases |
| No runtime dependencies beyond scikit-learn (already in Dockerfile) | Sensitive to max_depth tuning (underfit vs overfit) |
| Easy to explain to lecturer or evaluator | Single tree can be unstable with small data |

---

## Algorithm 2 — Isolation Forest

### Applicability Assessment

| Factor | Assessment |
|--------|-----------|
| Problem type | Unsupervised anomaly detection — **natural fit** |
| Need for labels | None — trains entirely on NORMAL readings — **ideal given no dataset** |
| Feature space | Works well in low-dimensional space — **good** |
| Inference cost | Forest of short trees, still sub-millisecond — **edge-ready** |
| Interpretability | Produces a continuous anomaly score, no explicit rule — **less transparent** |
| Concept drift | Can be retrained on new NORMAL windows in-band — **adaptable** |

**Verdict: excellent fit.** Isolation Forest is designed exactly for this scenario: you have abundant "normal" readings and rare anomalies, and labelling them is impractical. It isolates anomalies by building random trees and measuring how few splits are needed to isolate each point — anomalies are isolated quickly.

### How It Works

The algorithm builds `n_estimators` random trees. For each sample, it measures the average path length to isolation across all trees. Anomalies have short paths (easy to isolate); normal points have long paths (mixed with others). The output `decision_function` score is negative for anomalies; the `predict` output is -1 (anomaly) or 1 (normal).

### Training Strategy

1. **Warm-up phase** (first 200 readings after container start): collect readings without making control decisions — just fill a training buffer.
2. After 200 readings, fit `IsolationForest(n_estimators=100, contamination=0.05)` on those baseline readings.
3. Map the continuous score to three classes using two configurable thresholds.
4. Optionally re-fit every 1 000 new readings to adapt to hardware drift.

No offline data generation needed — the container trains itself from live sensor data.

### Score → Class Mapping

```
anomaly_score < THRESHOLD_CRITICAL → "CRITICAL"
THRESHOLD_CRITICAL ≤ score < THRESHOLD_WARNING → "WARNING"
score ≥ THRESHOLD_WARNING → "NORMAL"
```

Initial thresholds are tuned on the warm-up data at fit time using the 5th and 15th percentile of scores.

### Implementation Plan

**New file: `python/ml/isolation_forest.py`**

```python
import joblib, numpy as np
from pathlib import Path
from collections import deque
from sklearn.ensemble import IsolationForest
from .base import extract_features

MODEL_PATH    = Path("models/isolation_forest.joblib")
WARMUP_NEEDED = 200
RETRAIN_EVERY = 1_000

_model         = None
_is_fitted     = False
_buffer        = []          # raw feature rows during warm-up
_seen          = 0
_thresh_warn   = None
_thresh_crit   = None

def load_model():
    global _model, _is_fitted, _thresh_warn, _thresh_crit
    if MODEL_PATH.exists():
        saved = joblib.load(MODEL_PATH)
        _model, _is_fitted = saved["model"], True
        _thresh_warn, _thresh_crit = saved["thresh_warn"], saved["thresh_crit"]

def _fit(X):
    global _model, _is_fitted, _thresh_warn, _thresh_crit
    _model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    _model.fit(X)
    scores = _model.decision_function(X)
    _thresh_crit = float(np.percentile(scores, 5))
    _thresh_warn = float(np.percentile(scores, 15))
    _is_fitted = True
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"model": _model, "thresh_warn": _thresh_warn,
                 "thresh_crit": _thresh_crit}, MODEL_PATH)

def classify(temperature, window):
    global _buffer, _seen
    feat = extract_features(temperature, window)

    if not _is_fitted:
        _buffer.append(feat[0])
        if len(_buffer) >= WARMUP_NEEDED:
            _fit(np.array(_buffer))
        # during warm-up fall back to simple threshold
        z = feat[0][1]   # z_score index
        if temperature >= 90.0: return "CRITICAL", -1.0
        if temperature >= 85.0: return "WARNING",  -0.5
        return "NORMAL", float(z)

    _seen += 1
    if _seen % RETRAIN_EVERY == 0:
        _buffer.append(feat[0])
        if len(_buffer) > 5_000:
            _buffer = _buffer[-5_000:]
        _fit(np.array(_buffer))

    score = float(_model.decision_function(feat)[0])
    if score < _thresh_crit:
        return "CRITICAL", score
    if score < _thresh_warn:
        return "WARNING", score
    return "NORMAL", score
```

### Pros / Cons

| Pros | Cons |
|------|------|
| Zero labelled data required | "Black box" — score not as interpretable as a rule |
| Self-calibrates to actual hardware baseline | Warm-up period (first ~200 readings use fallback) |
| Naturally handles drift via periodic refit | Contamination hyperparameter needs tuning |
| Proven technique for industrial anomaly detection | Score thresholds need empirical validation |

---

## Algorithm 3 — Random Forest

### Applicability Assessment

| Factor | Assessment |
|--------|-----------|
| Problem type | Multi-class supervised classification — **good fit** |
| Robustness | Ensemble of 100 trees drastically reduces DT's instability — **better than single DT** |
| Feature importance | Built-in `.feature_importances_` — **useful for debugging sensor health** |
| Inference cost | ~100 tree traversals; still < 1 ms on modern CPUs — **edge-acceptable** |
| Labelled data | Same synthetic generation as Decision Tree — **solved** |
| Overfitting | Bootstrap + feature subsampling inherently regularises — **more reliable** |

**Verdict: strong fit.** Random Forest is the natural upgrade path from Decision Tree. It uses the same training pipeline but replaces one tree with an ensemble, yielding significantly better generalisation. It also provides class probability estimates, enabling soft WARNING/CRITICAL escalation.

### How It Works

Random Forest grows `n_estimators` Decision Trees, each trained on a bootstrap sample of the training data and a random subset of features per split. Predictions are determined by majority vote (or probability averaging). The diversity among trees reduces variance and overfitting.

### Training Strategy

Identical to the Decision Tree strategy:
1. Generate 10 000 synthetic samples using the same regime model.
2. Train `RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced")`.
3. Persist with `joblib.dump`.
4. Optionally run an optional **online refinement** step: once real CRITICAL/WARNING events occur (confirmed by Node-RED operator), add them to the training set and retrain.

### Class Probability Escalation

Random Forest outputs per-class probabilities. This enables a richer control signal:

```
P(CRITICAL) > 0.5  → "CRITICAL"
P(WARNING)  > 0.4  → "WARNING"   # lower threshold to catch borderline cases early
Otherwise          → "NORMAL"
```

This is more nuanced than a hard argmax and can be tuned without retraining.

### Implementation Plan

**New file: `python/ml/random_forest.py`**

```python
import joblib, numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from .base import extract_features, threshold_label

MODEL_PATH = Path("models/random_forest.joblib")
CLASSES    = ["NORMAL", "WARNING", "CRITICAL"]
_model     = None

# Probability thresholds — tune without retraining
P_CRITICAL = 0.50
P_WARNING  = 0.40

def _generate_training_data(n=10_000):
    # identical to decision_tree._generate_training_data
    import numpy as np
    from collections import deque
    rng = np.random.default_rng(42)
    regimes = [
        (77.0, 3.0,  "NORMAL",   0.7),
        (87.0, 2.0,  "WARNING",  0.2),
        (93.0, 1.5,  "CRITICAL", 0.1),
    ]
    X, y = [], []
    window = list(rng.normal(77, 3, 50))
    for _ in range(n):
        idx = rng.choice(3, p=[0.7, 0.2, 0.1])
        mu, sigma, label_str, _ = regimes[idx]
        temp = float(rng.normal(mu, sigma))
        dq = deque(window[-50:], maxlen=50)
        X.append(extract_features(temp, dq)[0])
        y.append(label_str)
        window.append(temp)
    return np.array(X), np.array(y)

def load_model():
    global _model
    if MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
        return
    X, y = _generate_training_data()
    _model = RandomForestClassifier(
        n_estimators=100, max_depth=8,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    _model.fit(X, y)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(_model, MODEL_PATH)

def classify(temperature, window):
    features = extract_features(temperature, window)
    proba    = _model.predict_proba(features)[0]
    p_crit   = proba[CLASSES.index("CRITICAL")]
    p_warn   = proba[CLASSES.index("WARNING")]

    if p_crit >= P_CRITICAL:
        return "CRITICAL", float(p_crit)
    if p_warn >= P_WARNING:
        return "WARNING",  float(p_warn)
    return "NORMAL", float(proba[CLASSES.index("NORMAL")])
```

**Dockerfile change** (none needed — scikit-learn already installed):
```
RUN pip install --no-cache-dir paho-mqtt numpy scikit-learn
```

### Pros / Cons

| Pros | Cons |
|------|------|
| More robust than single DT — handles noisy LDR readings better | Larger memory footprint (~100 trees vs 1) |
| Built-in feature importance for sensor diagnostics | Slower to train (acceptable offline) |
| Probability outputs enable soft escalation | Still relies on synthetic training data |
| Easy upgrade from DT — same training pipeline | Less interpretable than a single tree |

---

## Comparison Table

| | Decision Tree | Isolation Forest | Random Forest |
|--|--|--|--|
| **Paradigm** | Supervised classification | Unsupervised anomaly detection | Supervised classification (ensemble) |
| **Needs labels** | Yes (synthetic) | No | Yes (synthetic) |
| **Adapts to drift** | No (needs retrain) | Yes (periodic self-refit) | No (needs retrain) |
| **Interpretability** | High (printable tree) | Low (score) | Medium (feature importance) |
| **Inference speed** | Fastest | Fast | Fast |
| **Edge memory** | < 1 MB | ~5 MB | ~10 MB |
| **Best when** | You want explainable rules | Hardware baseline is unknown / shifts | You need robustness over a single DT |
| **Recommended order** | Start here | Try if DT struggles at baseline shifts | Upgrade path from DT |

---

## Implementation Order (Recommended)

1. **Build `ml/base.py`** — shared feature engineering, no algorithm dependency.
2. **Build `ml/decision_tree.py`** — simplest; validates the plug-and-play seam.
3. **Modify `edge_ai.py`** — add `load_model()` call + swap `classify` import.
4. **Verify end-to-end** — run `docker-compose up --build`, cover/uncover LDR, confirm Node-RED dashboard reacts identically to before.
5. **Add `ml/isolation_forest.py`** — test warm-up period, verify self-calibration.
6. **Add `ml/random_forest.py`** — compare with DT, observe whether probability thresholds need adjustment.

---

## Evaluation Metrics (in-system)

Since this is a real-time system with no ground truth, track these proxy metrics from the Node-RED alert log:

- **False positive rate** — fan activates when LDR is uncovered (temperature is normal).
- **Response latency** — readings between "cover LDR" event and first WARNING/CRITICAL alert.
- **Hysteresis stability** — number of spurious ON/OFF fan toggles per 5-minute window.
- **Score distribution** — log `score` field in alert payloads; a healthy system shows a bimodal distribution (cluster near 0 for NORMAL, cluster near 1 for anomalies).

No code changes needed in `edge_ai.py` to collect these — the `score` field is already included in every MQTT alert payload.
