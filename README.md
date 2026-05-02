# Motor Thermal Monitoring Digital Twin with Edge Anomaly Detection and Predictive Maintenance

> CO326 — Computer Systems Engineering & Industrial Networks | University of Peradeniya | 2026

---

## Group Members

| Name | Index Number |
|---|---|
| Haritha Bandara | E/20/037 |
| Yohan Senanayake | E/20/363 |
| Chamodi Senarathne | E/20/365 |
| Janith Wanasinghe | E/20/420 |

**Group 10 — Department of Computer Engineering**

---

## 📄 Report

The full project report is available in the repository:

📁 [`Report/Group10_Motor_Thermal_Monitoring_Digital_Twin_Report.pdf`](Report/Group10_Motor_Thermal_Monitoring_Digital_Twin_Report.pdf)

---

## Project Description

This project implements an **Edge AI-based Industrial IoT system** that monitors motor surface temperature in real time using an ESP32 microcontroller and an LDR (Light Dependent Resistor) as a proxy temperature sensor. Two complementary AI subsystems run in parallel from the same sensor stream:

- **Reactive Edge AI** — classifies each reading as NORMAL, WARNING, or CRITICAL and immediately drives a cooling fan relay. Four interchangeable algorithms are provided: Z-score baseline, Decision Tree, Isolation Forest, and Random Forest.
- **Predictive Maintenance Service** — analyses a sliding window of historical readings to estimate how many minutes remain before the motor crosses the warning threshold. Two models are supported: a linear slope extrapolation baseline and an LSTM neural network.

**Industrial Problem:** Detect motor overheating, thermal runaway, and cooling failure *before* they cause physical damage or production downtime.

**Key Features:**
- ESP32 with LDR sensor (or software simulator) publishes temperature every 2 seconds
- Four swappable reactive classification algorithms behind a unified two-function contract
- Automatic fan control with hysteresis (fan ON during anomaly, OFF after 5 consecutive NORMAL readings)
- Predictive service with 30–60 second early warning lead time ahead of threshold-based detection
- Manual fan override and AUTO/MANUAL mode switch via Node-RED dashboard
- Alert data forwarded to local historian (InfluxDB) and cloud SCADA (lecturer's broker)
- Grafana digital twin dashboard with live gauges, trend graphs, risk score overlay, and alert timeline

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  DEVICE LAYER (ESP32 + LDR / python-device simulator)            │
│  LDR ADC → linear temperature map (40–100 °C)                    │
│  Publishes: sensors/group10/motorTemp/data  (every 2 s)          │
└─────────────────────────┬────────────────────────────────────────┘
                          │ MQTT (local Mosquitto broker)
                          ▼
          ┌───────────────┴────────────────┐
          ▼                                ▼
┌──────────────────────┐       ┌───────────────────────────┐
│  REACTIVE EDGE AI    │       │  PREDICTIVE AI SERVICE     │
│  (python-edge)       │       │  (python-predict)          │
│  Z-score / DTree /   │       │  Baseline (linear slope)   │
│  IForest / RForest   │       │  or LSTM (30-step window)  │
│  Fan hysteresis      │       │  Read-only — never touches │
│  AUTO/MANUAL mode    │       │  fan relay                 │
└──────┬───────────────┘       └────────────┬──────────────┘
       │ MQTT (local + cloud)               │ MQTT (local)
       ▼                                    ▼
┌─────────────────────────┐       ┌──────────────────────────┐
│  HMI LAYER (Node-RED)   │       │  SCADA (Lecturer server)  │
│  Dashboard at :1880     │       │  Receives alerts only      │
│  Live chart, gauge,     │       │  (never raw sensor data)   │
│  alert log, fan control │       └──────────────────────────┘
│  mode switch            │
│  Writes to InfluxDB     │
└─────────────────────────┘
                │
                ▼
┌──────────────────────────┐
│  InfluxDB (Historian)    │
│  motor_thermal bucket    │
│  motor_alert measurement │
│  motor_prediction meas.  │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  Grafana Digital Twin    │
│  Live temp gauge         │
│  LSTM risk score overlay │
│  Alert status + timeline │
│  Fan state indicator     │
└──────────────────────────┘
```

The key architectural decision is the **clean separation between reactive and predictive AI layers**. Both containers subscribe to the same sensor topic but operate independently. Only `python-edge` can publish fan commands; `python-predict` is strictly read-only from a control perspective — a crash or miscalibration in the predictive service cannot affect fan control logic.

---

## Hardware

| Component | Detail |
|---|---|
| Microcontroller | ESP32 Dev Module (38-pin) |
| Sensor | LDR (photoresistor) with 10 kΩ pull-down resistor |
| Actuator | 5 V relay module (active-HIGH) driving a DC cooling fan |
| LDR GPIO | GPIO 34 (ADC1 — no WiFi conflict) |
| Relay GPIO | GPIO 12 (digital output) |

**Temperature mapping:** The 0–4095 ADC range is mapped linearly to 40–100 °C:

```
T = 40.0 + (ADC / 4095) × 60.0
```

In normal office lighting the LDR reads ~ADC 1800–2200 (≈65–72 °C). Fully covering the sensor pushes ADC above 3800 (>95 °C), reliably triggering a CRITICAL alert.

> **Why LDR instead of a thermistor?** Covering the sensor with a finger or dark paper raises the ADC reading instantly, letting the full system response cycle be demonstrated in seconds without a heat source.

> **GPIO 34 matters:** The ESP32's ADC2 bank is shared with the WiFi radio, causing erratic readings when WiFi is active. GPIO 34 belongs to ADC1 and is independent of the WiFi peripheral.

---

## MQTT Topics

| Topic | Publisher | Subscribers | Purpose |
|---|---|---|---|
| `sensors/group10/motorTemp/data` | ESP32 / simulator | python-edge, python-predict | Raw temperature every 2 s |
| `alerts/group10/motorTemp/status` | python-edge | Node-RED, cloud SCADA | Z-score anomaly alert |
| `control/group10/motorTemp/fan` | python-edge, Node-RED | ESP32 | Fan relay command |
| `control/group10/motorTemp/mode` | Node-RED | python-edge | AUTO/MANUAL mode (retained) |
| `predict/group10/motorTemp/risk` | python-predict | Node-RED, InfluxDB | Risk score 0–1, ETA minutes |

Raw sensor data is published **only to the local broker**. The edge AI forwards processed alerts — not raw readings — to the cloud SCADA broker, reducing outbound bandwidth and avoiding sending operational data off-site.

**Sensor payload:**
```json
{
  "temperature": 72.4,
  "timestamp": 1714232100.0,
  "fan_state": "OFF"
}
```

**Alert payload:**
```json
{
  "status": "WARNING",
  "temperature": 72.4,
  "z_score": 2.31,
  "fan_command": "ON",
  "timestamp": 1714232100.0
}
```

**Predictive payload:**
```json
{
  "risk_score": 0.73,
  "eta_minutes": 4.2,
  "model": "lstm",
  "timestamp": 1714232100.0
}
```

---

## Docker Compose Stack

| Service | Image | Port | Role |
|---|---|---|---|
| `mqtt` | eclipse-mosquitto:2.0 | 1883 | MQTT broker |
| `node-red` | nodered/node-red:latest | 1880 | Operator HMI |
| `python-edge` | custom Python 3.11 | — | Reactive edge AI |
| `python-predict` | custom Python 3.11 | — | Predictive maintenance service |
| `influxdb` | influxdb:2.7 | 8086 | Time-series historian |
| `grafana` | grafana/grafana:latest | 3000 | Digital twin dashboards |
| `python-device` | custom Python 3.11 | — | Software simulator (simulation profile) |

The `python-device` service runs under a Docker Compose **simulation profile**. When the real ESP32 is connected it stays off; when testing without hardware, run `docker compose --profile simulation up` to start it alongside everything else.

---

## Reactive Classification Algorithms

All four algorithms share the same two-function contract (`load_model()` / `classify(temperature, window)`) and the same five-feature vector:

| Feature | Formula | Why it matters |
|---|---|---|
| `temperature` | T | Absolute level |
| `z_score` | (T − μ) / σ | Deviation relative to recent history |
| `delta` | T − T_prev | Rate of change |
| `rolling_mean` | μ over last 50 readings | Recent operating baseline |
| `rolling_std` | σ over last 50 readings | Recent variability |

| Algorithm | Training | Labels needed | Adapts to drift | Best for |
|---|---|---|---|---|
| **Z-Score** (baseline) | None | No | No | Fallback / regression baseline |
| **Decision Tree** | Auto ~1 s | No (synthetic) | No | Explainable rules |
| **Isolation Forest** | Auto ~400 s live | No | Yes (periodic refit) | Unknown baseline environments |
| **Random Forest** | Auto ~3–5 s | No (synthetic) | No | Robust production use |

Switching algorithms requires changing **a single import line** in `edge_ai.py` and rebuilding the container.

---

## Predictive Maintenance Service

The predictive service estimates whether the warning threshold will be crossed within the next few minutes based on the previous 60 seconds of data (30 readings × 2 s interval).

**Phase 1 — Linear Slope Extrapolation (baseline):** Fits a linear regression to the last 15 readings and extrapolates to the warning threshold. Simple enough to reason about on paper; used to verify the entire pipeline before any neural network training.

**Phase 2 — LSTM Neural Network:**
- Input: 30 time steps × 3 features (temperature, delta, z-score)
- Architecture: LSTM(64) → Dropout(0.2) → Dense(32, ReLU) → Dense(1, sigmoid)
- Output: probability that the motor will cross T_WARNING within the next 10 readings
- Trained locally (not in Docker) to keep images lean; inference uses `tflite-runtime` (~5 MB)
- 50,000 synthetic labeled sequences; target AUC-ROC ≥ 0.95, accuracy ≥ 0.90

**Key result:** The LSTM risk score crosses 0.5 approximately **30–60 seconds before** the temperature reaches the 85 °C warning threshold, providing actionable lead time that threshold-only monitoring cannot.

The active model is selected by setting the `PREDICTIVE_MODEL` environment variable to `baseline` or `lstm` — no code change required.

---

## How to Run

### Prerequisites
- Docker Engine 24+ with Docker Compose plugin
- Git

### 1. Clone the repository

```bash
git clone https://github.com/cepdnaclk/e20-co326-Motor-Thermal-Monitoring-Digital-Twin.git
cd e20-co326-Motor-Thermal-Monitoring-Digital-Twin
```

### 2. Start the full stack

```bash
# With real ESP32
docker compose up --build

# With software simulator (no hardware required)
docker compose --profile simulation up --build
```

All services start automatically:

| Service | URL |
|---|---|
| Node-RED Dashboard | http://localhost:1880/dashboard |
| Node-RED Editor | http://localhost:1880 |
| InfluxDB | http://localhost:8086 |
| Grafana | http://localhost:3000 |
| MQTT Broker | localhost:1883 |

### 3. Verify the pipeline

```bash
# Device — temperature data publishing every 2 s
docker logs -f python-device

# Reactive edge AI — Z-score classification
docker logs -f python-edge
```

Expected output from `python-edge`:
```
[EDGE ] temp=72.40°C  z=+2.310  status=WARNING   ai_fan=ON   mode=AUTO  window=50
```

### 4. Switch the predictive model

Edit `docker-compose.yml` and set the environment variable on `python-predict`:

```yaml
python-predict:
  environment:
    - PREDICTIVE_MODEL=lstm   # or "baseline"
```

Then rebuild:
```bash
docker compose up --build python-predict
```

### 5. Connect to the lecturer's cloud SCADA broker

Edit `python/config.py` and set:

```python
CLOUD_BROKER = "192.168.x.x"   # replace with actual IP
```

Then rebuild:
```bash
docker compose up --build python-edge
```

### 6. Switch to a real ESP32

Stop the simulated device:
```bash
docker compose stop python-device
```

Flash your ESP32 to:
- Connect to this machine's IP on port `1883`
- Publish to `sensors/group10/motorTemp/data` every 2 seconds using the payload format above
- Subscribe to `control/group10/motorTemp/fan` and drive the relay accordingly

---

## Security Notes

> **MQTT broker authentication:** Anonymous access is enabled in `mosquitto/mosquitto.conf` (`allow_anonymous true`). This is intentional for the lab environment.
>
> **To re-enable auth:** Set `allow_anonymous false` and uncomment `password_file /mosquitto/config/passwd`. Generate a password file with: `mosquitto_passwd -c mosquitto/passwd <username>`
>
> **InfluxDB token:** A fixed admin token (`motor-token-group10`) is hardcoded in `docker-compose.yml`. This is acceptable in a lab environment; for production, move secrets to a `.env` file and rotate the token.

---

## Challenges and Solutions

| Challenge | Root Cause | Solution |
|---|---|---|
| Erratic LDR readings | GPIO 13 (ADC2) shares the WiFi radio | Moved to GPIO 34 (ADC1), independent of WiFi |
| Spurious cold-start warnings | Near-zero σ with 2–3 readings inflates z-scores | `MIN_READINGS = 10` guard before any classification |
| Isolation Forest silent warm-up | 400 s live warm-up gave no feedback | Per-reading progress log + Node-RED "warming up" indicator |
| LSTM class imbalance | Random simulation produced <1% anomalies | Sticky Regime-Based Sampling across three Gaussian regimes |
| Async MQTT vs sequential LSTM input | MQTT delivers one reading at a time | Thread-safe `SlidingBuffer` adapter with warm-up period |
| InfluxDB token on first run | No token exists before setup | `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` env var creates it at first run |
| Node-RED flow merge conflicts | Shared `flows.json` caused Git conflicts | Predictive flows split into `flows-predict.json`; Node-RED auto-merges all `flows*.json` |
| `tflite-runtime` arch compatibility | PyPI wheel not available for all platforms | Graceful fallback to full TensorFlow; clear error with install guidance |

---

## Member Contributions

| Member | Primary Contributions |
|---|---|
| **Haritha Bandara** | System architecture design; `edge_ai.py` (MQTT orchestration, dual-publish pattern, fan hysteresis, AUTO/MANUAL mode); `config.py`; Docker Compose coordination; cloud SCADA integration; overall project structure; report sections 1, 2, 5, 9, 10 |
| **Yohan Senanayake** | `ml/` package: `base.py` (shared feature engineering, synthetic data generation), `z_score.py`, `decision_tree.py`, `isolation_forest.py`, `random_forest.py`; warm-up logging and dashboard indicator for Isolation Forest; developer documentation (`ml/README.md`); report section 6 |
| **Chamodi Senarathne** | `predictive/` package (buffer, features, baseline model, LSTM, model registry); `predictive_service.py`; offline LSTM training pipeline; Node-RED predictive flow (`flows-predict.json`) with InfluxDB write nodes; InfluxDB service and data model; Grafana digital twin dashboard; Docker Compose additions; report section 7 |
| **Janith Wanasinghe** | Unified `docker-compose.yml` (six-service stack); InfluxDB historian integration and Node-RED data routing; Grafana dashboard (`motor-health-dashboard.json`) with custom Flux queries; automated datasource and dashboard provisioning; system integration and debugging; comprehensive system documentation; report sections 3, 4 |

---

## Future Work

- **On-device inference** — Run classification directly on the ESP32 using TensorFlow Lite for Microcontrollers, eliminating the Python containers for the reactive path
- **Online learning** — Refine supervised models in the background when an operator confirms a genuine WARNING event
- **Multi-motor aggregation** — Each motor gets its own MQTT topic prefix; a single Grafana dashboard queries multiple InfluxDB buckets
- **Security hardening** — Add MQTT TLS, client certificates, and proper secret management for the InfluxDB token
- **RUL estimation** — Estimate Remaining Useful Life from the trend in alert frequency and thermal baseline drift over months of InfluxDB history
