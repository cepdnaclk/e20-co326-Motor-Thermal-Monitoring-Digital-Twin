# Predictive Maintenance Model — Implementation Plan

> **Author:** [Your name]  
> **Project root:** `LDR-Hardware-simulation/` — this IS the active project directory; the repo root is the original software-only simulation and is no longer the primary working folder  
> **Hardware requirement:** None — all testing is done via software simulation (`mqtt_publisher.py`)  
> **Status:** Draft

---

## 1. Context & Motivation

### Current State of the Repo

> **Important:** `LDR-Hardware-simulation/` is the **active project root**. The repo root contains the original software-only simulation (first teammate's work) and is no longer the primary folder. All new services must be added to `LDR-Hardware-simulation/docker-compose.yml`.

| Layer | What exists in `LDR-Hardware-simulation/` today |
|---|---|
| **Device** | Real ESP32 + LDR (hardware); `python/mqtt_publisher.py` kept as software fallback |
| **Edge AI** | `python/edge_ai.py` — z-score + absolute threshold classifier (WARNING/CRITICAL) |
| **ML upgrade (in progress)** | `ml-control-plan.md` + `python/ml/` — teammates adding Decision Tree / Isolation Forest / Random Forest |
| **Stack** | Mosquitto + Node-RED + Python Edge via `docker-compose.yml` |
| **Historian** | ❌ InfluxDB not yet in this folder's `docker-compose.yml` — **must be added** (done in §8) |
| **Dashboard** | ❌ Grafana not yet in this folder's `docker-compose.yml` — **must be added** (done in §8) |

### What This Plan Adds

The edge ML upgrade (teammates' work) reacts to **current** temperature readings. This plan adds a **separate predictive service** that operates on **historical sequences** and answers a different question:

> *"Given the last N minutes of temperature readings, how likely is the motor to overheat in the next K minutes?"*

The output is a **risk score and estimated time-to-anomaly** published on a new MQTT topic. Node-RED and Grafana consume this to display a "⚠️ Predicted overheat in ~8 min" style alert.

### Design Principles

- **Zero hardware dependency** — the predictive service works with the software simulator (`mqtt_publisher.py`) and can be run without an ESP32.  
- **Non-intrusive** — existing `edge_ai.py` and teammates' ML work are untouched. New service runs in a new Docker container.  
- **Modular** — placed entirely in `LDR-Hardware-simulation/python/predictive/`.  
- **Swappable model** — a simple baseline (linear regression on rolling slope) ships first; LSTM is the upgrade path.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│ LDR-Hardware-simulation/                                         │
│                                                                  │
│  [ESP32 / mqtt_publisher.py]                                     │
│         │  sensors/group10/motorTemp/data                        │
│         ▼                                                        │
│  ┌─────────────┐       ┌─────────────────────────────────────┐  │
│  │  edge_ai.py │       │  predictive_service.py  (NEW)        │  │
│  │  (teammates)│       │                                      │  │
│  │  z-score/ML │       │  Sliding buffer of last N readings   │  │
│  │  → WARNING  │       │  → Feature extraction                │  │
│  │  → CRITICAL │       │  → Model inference                   │  │
│  │  → fan ctrl │       │  → risk_score, eta_minutes           │  │
│  └──────┬──────┘       └──────────────┬──────────────────────┘  │
│         │                             │                          │
│         ▼                             ▼                          │
│  alerts/group10/motorTemp/status      predict/group10/motorTemp/risk │
│         │                             │                          │
│         └──────────────┬──────────────┘                         │
│                        ▼                                         │
│                  [Mosquitto]                                      │
│                        │                                         │
│            ┌───────────┴────────────┐                            │
│            ▼                        ▼                            │
│        [Node-RED]             [InfluxDB 2.7]                     │
│        Dashboard              Historical store                    │
│            │                        │                            │
│            └───────────┬────────────┘                            │
│                        ▼                                         │
│                    [Grafana]                                      │
│             Predictive Risk Panel (NEW)                          │
└──────────────────────────────────────────────────────────────────┘
```

### New MQTT Topic Contract

| Topic | Publisher | Payload |
|---|---|---|
| `predict/group10/motorTemp/risk` | `predictive_service.py` | `{"risk_score": 0.0–1.0, "eta_minutes": float\|null, "model": "string", "timestamp": float}` |

- `risk_score = 0.0` → no predicted risk; `1.0` → imminent anomaly  
- `eta_minutes` → estimated minutes until WARNING threshold is breached; `null` if not trending toward it  
- `model` → name of the active model (for logging / dashboard label)

---

## 3. File Layout

Files to **create** (all inside `LDR-Hardware-simulation/`):

```
LDR-Hardware-simulation/
├── python/
│   ├── predictive/
│   │   ├── __init__.py                  ← makes it a package
│   │   ├── buffer.py                    ← sliding window data buffer
│   │   ├── features.py                  ← feature engineering shared by all models
│   │   ├── baseline_model.py            ← Phase 1: linear slope extrapolation
│   │   ├── lstm_model.py                ← Phase 2: LSTM sequence model
│   │   └── model_registry.py            ← single import point; swap via env var
│   ├── predictive_service.py            ← MQTT subscriber → model → publisher
│   ├── generate_training_data.py        ← offline script: produce CSV from simulator
│   └── train_lstm.py                    ← offline script: train & save LSTM weights
│
├── models/                              ← saved model artefacts (git-ignored)
│   └── lstm_motor.keras                 ← output of train_lstm.py
│
├── data/                                ← synthetic/collected CSVs (git-ignored)
│   └── motor_training.csv               ← output of generate_training_data.py
│
├── tests/
│   ├── test_buffer.py
│   ├── test_features.py
│   ├── test_baseline_model.py
│   └── test_predictive_service.py       ← integration test with mock MQTT
│
├── node-red/
│   └── flows-predict.json               ← NEW separate Node-RED flow file (risk gauge + InfluxDB write)
│
└── docker-compose.yml                   ← add python-predict service + influxdb + grafana
```

Files to **modify**:

```
LDR-Hardware-simulation/
├── docker-compose.yml                   ← add python-predict + influxdb + grafana services
└── python/
    ├── Dockerfile                       ← add scikit-learn + influxdb-client (NOT tensorflow)
    └── requirements.txt                 ← add scikit-learn, influxdb-client
```

> **tensorflow is NOT added to the Docker image.** LSTM training runs locally (see §5). The container only loads the pre-trained `.keras` file, using `tflite-runtime` for inference — much lighter than full TensorFlow.

---

## 4. Phase 1 — Baseline Model (Linear Slope Extrapolation)

### Why start here

Before training any neural network, a simple model lets you verify the full pipeline (MQTT → buffer → inference → publish → dashboard) with zero training time and no GPU.

### How it works

1. Maintain a rolling buffer of the last `BUFFER_SIZE = 30` temperature readings (60 seconds at 2 s/reading).  
2. Fit a linear regression on the last `SLOPE_WINDOW = 15` readings (30 seconds).  
3. Extrapolate: how many minutes until the trendline crosses `T_WARNING = 85.0 °C`?  
4. Compute `risk_score` from the slope — steeper rise = higher risk.

```
slope = (T[now] - T[now - SLOPE_WINDOW]) / SLOPE_WINDOW   # °C per reading

if slope > 0:
    readings_to_warning = (T_WARNING - T[now]) / slope
    eta_minutes = readings_to_warning * 2 / 60             # 2 s per reading
    risk_score  = min(1.0, slope / MAX_SLOPE)              # normalised
else:
    eta_minutes = None
    risk_score  = 0.0
```

### Implementation: `python/predictive/baseline_model.py`

```python
from __future__ import annotations
import numpy as np
from .buffer import SlidingBuffer
from .features import extract_slope

T_WARNING  = 85.0   # °C
MAX_SLOPE  = 1.5    # °C/reading that maps to risk_score = 1.0
READING_INTERVAL_S = 2

def predict(buf: SlidingBuffer) -> dict:
    """
    Returns {"risk_score": float, "eta_minutes": float|None, "model": str}
    Requires at least 10 readings in the buffer.
    """
    if len(buf) < 10:
        return {"risk_score": 0.0, "eta_minutes": None, "model": "baseline"}

    readings = np.array(buf.latest(15))
    slope    = extract_slope(readings)   # °C per reading
    current  = readings[-1]

    if slope > 0 and current < T_WARNING:
        readings_needed = (T_WARNING - current) / slope
        eta_minutes = (readings_needed * READING_INTERVAL_S) / 60.0
    else:
        eta_minutes = None

    risk_score = float(np.clip(slope / MAX_SLOPE, 0.0, 1.0))
    return {"risk_score": risk_score, "eta_minutes": eta_minutes, "model": "baseline"}
```

---

## 5. Phase 2 — LSTM Model

### Why LSTM

The temperature signal is a **time series with memory** — a motor heating slowly over 10 minutes looks different from a sudden spike, even at the same instantaneous temperature. LSTM can learn these temporal patterns from historical sequences.

### Model architecture

```
Input:  (batch, SEQUENCE_LEN=30, FEATURES=3)   ← [temperature, delta, z_score]
        ↓
LSTM(64 units, return_sequences=False)
        ↓
Dropout(0.2)
        ↓
Dense(32, activation='relu')
        ↓
Dense(1, activation='sigmoid')                 ← risk_score ∈ [0, 1]
```

**Label definition:** A sequence is labelled `risk = 1` if, within the next `HORIZON = 10` readings (20 seconds), the temperature crosses `T_WARNING`. Otherwise `risk = 0`.

### Training: Run Locally, Not in Docker

**Decision:** LSTM training runs locally on your machine using the `uv` environment already set up in the repo (`.python-version` + `pyproject.toml`). The Docker image does **not** install TensorFlow — it only loads the pre-trained model file at inference time.

**Why local:**
- Training is a one-time offline task. Putting TensorFlow in Docker just to train once inflates the image by ~900 MB and slows every `docker compose up --build`.
- The repo already has `uv` configured — zero extra setup needed.
- Much faster iteration when tuning hyperparameters (edit → run → check metrics, no Docker rebuild).
- The trained `.keras` file is mounted into the container via a volume — not baked into the image.

**Local setup (one time):**
```bash
# From LDR-Hardware-simulation/python/
uv pip install tensorflow numpy scikit-learn pandas
```

**Run training:**
```bash
# Step 1 — generate synthetic dataset (no MQTT needed)
python generate_training_data.py --samples 50000 --out ../data/motor_training.csv

# Step 2 — train and save model
python train_lstm.py --data ../data/motor_training.csv --epochs 30
# Output: ../models/lstm_motor.keras

# Step 3 — switch container to LSTM
# In docker-compose.yml: PREDICTIVE_MODEL=lstm
# Then: docker compose up --build
```

**Training data strategy (no hardware needed):**

Training data is generated entirely from `mqtt_publisher.py`'s simulation logic. The script runs the simulator in-process — no MQTT, no Docker, no ESP32.

Simulation logic reference (`mqtt_publisher.py`):
- Base temperature: `65 + 3*sin(t/20) + noise`
- Anomaly: 10% chance of +10–20 °C spike (CRITICAL), 15% chance of +4–7 °C spike (WARNING)

| Class | % of sequences | How produced |
|---|---|---|
| NORMAL (no anomaly ahead) | 65% | Baseline sine curve, no spike for next 10 readings |
| WARNING-ahead | 20% | WARNING spike injected within next 10 readings |
| CRITICAL-ahead | 15% | CRITICAL spike injected within next 10 readings |

Target dataset size: **50 000 sequences** (~10 seconds to generate).

### Implementation: `python/generate_training_data.py`

```python
"""
Offline script — runs locally, no MQTT or Docker needed.
Simulates the motor sensor in-process and writes labelled sequences to CSV.

Usage:
    python generate_training_data.py --samples 50000 --out ../data/motor_training.csv
"""
```

### Implementation: `python/train_lstm.py`

```python
"""
Offline script — runs locally after generate_training_data.py.
Trains the LSTM and saves the model for mounting into the Docker container.

Usage:
    python train_lstm.py --data ../data/motor_training.csv --epochs 30
    # Output: ../models/lstm_motor.keras
"""
```

### Keras model definition

```python
import tensorflow as tf

def build_model(seq_len=30, n_features=3):
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, input_shape=(seq_len, n_features)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid'),
    ])
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')],
    )
    return model
```

---

## 6. Swappable Model Registry

One env var controls which model is active — no code change needed to switch.

### `python/predictive/model_registry.py`

```python
import os

ACTIVE_MODEL = os.getenv("PREDICTIVE_MODEL", "baseline")   # or "lstm"

def get_predictor():
    if ACTIVE_MODEL == "lstm":
        from .lstm_model import predict
    else:
        from .baseline_model import predict
    return predict
```

### Docker environment variable

```yaml
# docker-compose.yml (python-predict service)
environment:
  - PREDICTIVE_MODEL=baseline    # change to "lstm" after training
```

---

## 7. `predictive_service.py` — Main Orchestrator

```python
"""
Subscribes to: sensors/group10/motorTemp/data
Publishes to:  predict/group10/motorTemp/risk

Runs as a standalone Docker container (python-predict).
"""
import json, time
import paho.mqtt.client as mqtt
from predictive.buffer import SlidingBuffer
from predictive.model_registry import get_predictor
from config import LOCAL_BROKER, PORT, SENSOR_TOPIC

PREDICT_TOPIC = "predict/group10/motorTemp/risk"
BUFFER_SIZE   = 30    # 60 seconds of readings

buf       = SlidingBuffer(maxlen=BUFFER_SIZE)
predictor = get_predictor()

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    buf.append(data["temperature"])

    result = predictor(buf)
    payload = {
        **result,
        "timestamp": data.get("timestamp", time.time()),
    }
    client.publish(PREDICT_TOPIC, json.dumps(payload))
    print(f"[PREDICT] risk={result['risk_score']:.3f}  eta={result['eta_minutes']}min  model={result['model']}")

client = mqtt.Client(client_id="predictive-service")
client.on_message = on_message
client.connect(LOCAL_BROKER, PORT, 60)
client.subscribe(SENSOR_TOPIC)
client.loop_forever()
```

---

## 8. Docker Integration

### Changes to `LDR-Hardware-simulation/docker-compose.yml`

```yaml
version: "3.8"

services:
  mqtt:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf

  node-red:
    image: nodered/node-red:latest
    ports:
      - "1880:1880"
    volumes:
      - ./node-red:/data
    depends_on:
      - mqtt

  python-edge:
    build: ./python
    command: python -u edge_ai.py
    environment:
      - PYTHONUNBUFFERED=1
    depends_on:
      - mqtt

  # ── NEW: Predictive Maintenance Service ─────────────────────────
  python-predict:
    build: ./python
    command: python -u predictive_service.py
    environment:
      - PYTHONUNBUFFERED=1
      - PREDICTIVE_MODEL=baseline        # swap to "lstm" after training
    volumes:
      - ./models:/app/models             # mount trained model artefacts
    depends_on:
      - mqtt
    restart: unless-stopped

  # ── NEW: InfluxDB (time-series historian) ───────────────────────
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    volumes:
      - influxdb_data:/var/lib/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword
      - DOCKER_INFLUXDB_INIT_ORG=group10
      - DOCKER_INFLUXDB_INIT_BUCKET=motor_thermal
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=motor-token-group10

  # ── NEW: Grafana ─────────────────────────────────────────────────
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - influxdb

  # ── Software simulator (use when no ESP32 available) ────────────
  python-device:
    build: ./python
    command: python -u mqtt_publisher.py
    environment:
      - PYTHONUNBUFFERED=1
    depends_on:
      - mqtt
    profiles:
      - simulation    # only starts when: docker compose --profile simulation up

volumes:
  influxdb_data:
  grafana_data:
```

> **Note for teammates:** The `python-device` service is placed under the `simulation` profile so it does NOT start by default when hardware (ESP32) is connected. Run `docker compose --profile simulation up` when testing without hardware.

### Changes to `LDR-Hardware-simulation/python/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

### `LDR-Hardware-simulation/python/requirements.txt` (new/updated)

```
paho-mqtt>=1.6
numpy>=1.24
scikit-learn>=1.3        # for baseline linear regression + feature helpers
tflite-runtime>=2.14     # lightweight LSTM inference only (NOT full tensorflow)
influxdb-client>=1.38    # InfluxDB writes from predict service
```

> **Note:** `tflite-runtime` (~5 MB) handles LSTM inference in the container. Full `tensorflow` (~900 MB) is only needed locally for training and is **never** installed in Docker.

---

## 9. Node-RED Integration — `flows-predict.json`

**Decision:** Predictive flows are kept in a **separate file** (`node-red/flows-predict.json`) to avoid merge conflicts with teammates' existing `flows.json`.

### How Node-RED loads multiple flow files

Node-RED merges all `.json` files in its `/data` directory that match the pattern `flows*.json`. Since the `node-red/` folder is mounted as `/data`, placing `flows-predict.json` alongside the existing `flows.json` means Node-RED automatically loads both on startup — no config changes needed.

### Flow A — Predictive Risk Gauge (UI)

```
MQTT In  →  topic: predict/group10/motorTemp/risk
  ↓
JSON parse
  ↓
├─→ ui_gauge     ("Anomaly Risk", 0–100%, thresholds: 30=orange, 60=red)
├─→ ui_text      ("⚠️ Overheat in {{eta_minutes | round(1)}} min" or "✅ No risk predicted")
└─→ ui_chart     (risk_score over time, overlaid on temperature chart)
```

### Flow B — Write Prediction to InfluxDB

```
MQTT In  →  topic: predict/group10/motorTemp/risk
  ↓
JSON parse
  ↓
function node  →  build InfluxDB point:
    measurement: "motor_prediction"
    fields: { risk_score, eta_minutes }
    tags:   { model, group_id: "group10" }
  ↓
InfluxDB Out  →  bucket: motor_thermal
                 org:    group10
                 token:  motor-token-group10
```

This enables a Grafana panel overlaying the actual temperature line with the predicted risk score over time.

---

## 10. Grafana Dashboard Panel

Add a new panel to the existing Grafana dashboard:

| Setting | Value |
|---|---|
| Panel type | Stat + Time series overlay |
| InfluxDB measurement | `motor_prediction` |
| Field | `risk_score` |
| Thresholds | 0–0.3 green, 0.3–0.6 orange, 0.6–1.0 red |
| Title | "Predicted Anomaly Risk" |
| Unit | Percent (0–100) |

Optional second panel: **"Estimated Time to Overheat"** (stat panel, unit: minutes, null displayed as "—").

---

## 11. Testing Strategy (No Hardware Required)

All tests run using `mqtt_publisher.py` as the data source. No ESP32 needed.

### 11.1 Unit Tests

| Test file | What it tests |
|---|---|
| `tests/test_buffer.py` | SlidingBuffer append, maxlen, latest(n) |
| `tests/test_features.py` | extract_slope with known arrays; edge cases (flat, descending) |
| `tests/test_baseline_model.py` | predict() output shape, risk_score range [0,1], eta_minutes > 0 when trending up |

Run with:
```bash
cd LDR-Hardware-simulation/python
python -m pytest ../tests/ -v
```

### 11.2 Integration Test (Software Simulation)

**Scenario A — Normal operation:**
```bash
docker compose --profile simulation up
# Observe: risk_score stays below 0.2; eta_minutes is null most of the time
```

**Scenario B — Simulated anomaly:**
Edit `mqtt_publisher.py` temporarily to force a sustained rising temperature (increase `anomaly` probability to 0.8):
```python
r = 0.0   # forces CRITICAL path always
anomaly = random.uniform(10, 20)
```
Expected output:
- `risk_score` rises above 0.6 within 30 seconds
- `eta_minutes` becomes non-null and decreasing
- Edge AI (`edge_ai.py`) fires WARNING/CRITICAL concurrently

**Scenario C — Fan cooling response:**
Verify that after `edge_ai.py` triggers the fan ON, the temperature drops, and `risk_score` returns below 0.3 within 60 seconds.

### 11.3 Model Evaluation (LSTM only)

Run offline after training — `train_lstm.py --eval` prints all metrics automatically:

```bash
# From LDR-Hardware-simulation/python/
python train_lstm.py --data ../data/motor_training.csv --epochs 30 --eval
```

**Target metrics on held-out 20% test split:**

| Metric | Target | Why it matters |
|---|---|---|
| **AUC-ROC** | ≥ 0.95 | Overall binary classification quality; threshold-independent |
| **Accuracy** | ≥ 0.90 | Overall correctness on balanced test set |
| **False Positive Rate** | ≤ 10% | How often `risk_score > 0.5` when motor is actually fine — high FPR destroys operator trust |
| **Early Warning Lead Time** | ≥ 20 s | How many seconds *before* edge AI fires WARNING does LSTM raise `risk_score > 0.5` |

**How to measure Early Warning Lead Time in practice:**
1. Run Scenario B (forced anomaly)
2. Record timestamp of first `risk_score > 0.5` on `predict/` topic
3. Record timestamp of first `status=WARNING` on `alerts/` topic
4. `lead_time = alerts_timestamp − predict_timestamp`

**For the project report:** Generate a time-series plot showing:
- Blue line: actual temperature
- Orange line: `risk_score × 100` (scaled to same axis)
- Red vertical marker: "Edge AI WARNING fired"
- Green vertical marker: "Predictive alert fired" (earlier)

The visual gap between the two markers is the most compelling result — it directly proves predictive value over reactive monitoring.

### 11.4 Regression Test

Ensure the predictive service does NOT interfere with teammates' edge ML work:
- Both `python-edge` and `python-predict` containers run simultaneously
- Fan control is still driven solely by `edge_ai.py` (predictive service is read-only / never publishes to `FAN_TOPIC`)

---

## 12. Implementation Order

```
Phase 1 — Foundation (no training needed)
──────────────────────────────────────────
[ ] 1. Create python/predictive/__init__.py, buffer.py, features.py
[ ] 2. Implement baseline_model.py (linear slope extrapolation)
[ ] 3. Implement model_registry.py
[ ] 4. Implement predictive_service.py
[ ] 5. Update docker-compose.yml (add python-predict, influxdb, grafana; profile simulation)
[ ] 6. Update python/Dockerfile + requirements.txt
[ ] 7. Write unit tests: test_buffer.py, test_features.py, test_baseline_model.py
[ ] 8. Run: docker compose --profile simulation up → verify MQTT output on predict/ topic
[ ] 9. (Optional) Add Node-RED flows for risk gauge + InfluxDB write

Phase 2 — LSTM Model (after Phase 1 is verified)
─────────────────────────────────────────────────
[ ] 10. Implement generate_training_data.py (offline, no MQTT)
[ ] 11. Run: python generate_training_data.py → confirm data/motor_training.csv
[ ] 12. Implement lstm_model.py
[ ] 13. Implement train_lstm.py
[ ] 14. Run: python train_lstm.py → confirm models/lstm_motor.keras
[ ] 15. Set PREDICTIVE_MODEL=lstm in docker-compose.yml
[ ] 16. Rebuild container, run integration tests (Scenarios A, B, C)
[ ] 17. Compare LSTM vs baseline on Scenario B response latency

Phase 3 — Polish (optional, time permitting)
────────────────────────────────────────────
[ ] 18. Add Grafana panel: Predicted Anomaly Risk overlay
[ ] 19. Write test_predictive_service.py (mock MQTT broker)
[ ] 20. Add online learning: periodically refine model from confirmed anomaly events
```

---

## 12b. Resolved Design Decisions

All open questions from the original draft have been answered:

| Question | Decision |
|---|---|
| InfluxDB credentials | **Hardcoded** in `docker-compose.yml` — no `.env` file needed for this folder |
| Node-RED flows | **Separate `flows-predict.json`** — auto-loaded by Node-RED alongside existing `flows.json`; zero merge conflict |
| LSTM training location | **Run locally** with `uv` — no TensorFlow in Docker; model file mounted as a volume |
| Container inference | Uses `tflite-runtime` (~5 MB) instead of full TensorFlow (~900 MB) |
| Evaluation criteria | **AUC-ROC**, **FPR**, **Early Warning Lead Time** — see §11.3 for detail |

---

## 13. Coordination Notes for Teammates

> **Read this section before touching any shared files.**

### What this plan touches

| File | Action | Impact on teammates |
|---|---|---|
| `docker-compose.yml` | **MODIFY** — add 3 new services | ⚠️ Merge carefully; use separate service blocks |
| `python/Dockerfile` | **MODIFY** — add deps | Low risk; additive only |
| `python/requirements.txt` | **CREATE/MODIFY** | Additive; may increase build time |
| `python/edge_ai.py` | **NOT TOUCHED** | No impact |
| `python/ml/` (teammates' dir) | **NOT TOUCHED** | No impact |
| `python/predictive/` | **CREATE new dir** | Isolated; no conflict |
| `python/predictive_service.py` | **CREATE new file** | Isolated; no conflict |

### MQTT topic ownership

| Topic | Owner |
|---|---|
| `sensors/group10/motorTemp/data` | Device / ESP32 |
| `alerts/group10/motorTemp/status` | `edge_ai.py` (teammates) |
| `control/group10/motorTemp/fan` | `edge_ai.py` (teammates) |
| `predict/group10/motorTemp/risk` | **`predictive_service.py` (this plan)** — new, no conflict |

The predictive service **subscribes** to the sensor topic (read-only) and **publishes** only to its own new topic. It never touches the fan control topic.

### Git workflow

1. Work on a feature branch: `git checkout -b feature/predictive-maintenance`
2. Do not rebase onto teammates' ML branch until both features are individually tested
3. When merging `docker-compose.yml`, manually resolve conflicts keeping all services

---

## 14. Remaining Open Questions

Only one question remains open — confirm before starting Phase 2:

1. **LSTM model size vs. accuracy trade-off** — The architecture proposed (64-unit LSTM) is a starting point. If accuracy on the test split is below target, increase to 128 units. If inference in the container is too slow (unlikely on modern hardware), reduce to 32. Measure with `time.time()` around the `predictor(buf)` call in `predictive_service.py`.

---

## 15. File Reference Summary

| File | Status | Description |
|---|---|---|
| `python/predictive/__init__.py` | CREATE | Package marker |
| `python/predictive/buffer.py` | CREATE | `SlidingBuffer` class |
| `python/predictive/features.py` | CREATE | `extract_slope`, `extract_features` |
| `python/predictive/baseline_model.py` | CREATE | Phase 1 linear extrapolation model |
| `python/predictive/lstm_model.py` | CREATE | Phase 2 LSTM inference wrapper (uses `tflite-runtime`) |
| `python/predictive/model_registry.py` | CREATE | Env-var-driven model selector |
| `python/predictive_service.py` | CREATE | MQTT orchestrator / main entry point |
| `python/generate_training_data.py` | CREATE | **Local only** — generate synthetic CSV from simulator |
| `python/train_lstm.py` | CREATE | **Local only** — train LSTM, save `.keras`; run with `uv` |
| `python/requirements.txt` | MODIFY | Add scikit-learn, tflite-runtime, influxdb-client (no tensorflow) |
| `python/Dockerfile` | MODIFY | Reference updated requirements.txt |
| `docker-compose.yml` | MODIFY | Add python-predict, influxdb (hardcoded creds), grafana, simulation profile |
| `node-red/flows-predict.json` | CREATE | Separate Node-RED flow: risk gauge + InfluxDB writer |
| `tests/test_buffer.py` | CREATE | Unit tests for buffer |
| `tests/test_features.py` | CREATE | Unit tests for feature extraction |
| `tests/test_baseline_model.py` | CREATE | Unit tests for baseline model |
| `tests/test_predictive_service.py` | CREATE | Integration test with mock broker |
| `models/` | CREATE dir | Git-ignored; holds `.keras` artefacts (output of local training) |
| `data/` | CREATE dir | Git-ignored; holds training CSVs (output of local data generation) |
