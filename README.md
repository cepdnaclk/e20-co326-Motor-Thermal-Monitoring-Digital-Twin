# Motor Health Monitoring Digital Twin with Edge Anomaly Detection

> CO326 — Computer Systems Engineering & Industrial Networks | University of Peradeniya | 2026

---

## Group Members

| Name | Index |
|---|---|
| Janith | e20-xxx |
| (Teammate 2) | (index) |
| (Teammate 3) | (index) |

---

## Project Description

This project implements an **Edge AI-based Industrial IoT system** that monitors motor surface temperature in real time, detects anomalies at the edge using Z-score statistical analysis, and controls a cooling fan relay to protect the motor from thermal damage.

**Industrial Problem:** Detect motor overheating, thermal runaway, and cooling failure before they cause physical damage or production downtime.

**Key features:**
- Simulated motor device (or real ESP32) publishes temperature every 2 seconds
- Edge AI layer applies Z-score anomaly detection on a rolling 50-reading window
- Automatic fan control with hysteresis (fan ON during anomaly, OFF after 5 consecutive NORMAL readings)
- Manual fan override and AUTO/MANUAL mode switch via Node-RED dashboard
- Alert data forwarded to both local historian (InfluxDB) and cloud SCADA (lecturer's broker)
- Grafana digital twin dashboard with live gauges, trend graphs, and alert timeline

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  DEVICE LAYER (python-device container / real ESP32)             │
│  Simulates motor + temperature sensor + fan relay                │
│  Publishes: sensors/group10/motorTemp/data  (every 2 s)          │
└─────────────────────────┬────────────────────────────────────────┘
                          │ MQTT (local Mosquitto broker)
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  EDGE AI LAYER (python-edge container)                           │
│  Z-score anomaly detection on rolling 50-reading window          │
│  Fan control with hysteresis (AUTO mode)                         │
│  Publishes alerts locally + to cloud SCADA broker                │
└──────┬──────────────────────────────────────┬────────────────────┘
       │ MQTT (local broker)                  │ MQTT (cloud broker)
       ▼                                      ▼
┌─────────────────────────┐       ┌──────────────────────────┐
│  HMI LAYER (Node-RED)   │       │  SCADA (Lecturer server)  │
│  Dashboard at :1880     │       │  Receives alerts only      │
│  Live chart, gauge,     │       │  (never raw sensor data)   │
│  alert log, fan control │       └──────────────────────────┘
│  mode switch            │
│  Writes to InfluxDB ───────────────────────────────────────┐
└─────────────────────────┘                                  │
                                                             ▼
                                              ┌──────────────────────────┐
                                              │  InfluxDB (Historian)     │
                                              │  motor_thermal_v2 bucket  │
                                              └────────────┬─────────────┘
                                                           │
                                                           ▼
                                              ┌──────────────────────────┐
                                              │  Grafana Digital Twin     │
                                              │  Live temp gauge          │
                                              │  Z-score trend            │
                                              │  Alert status + timeline  │
                                              │  Fan state indicator      │
                                              └──────────────────────────┘
```

---

## MQTT Topics Used

| Topic | Format | Publisher | Subscribers | Purpose |
|---|---|---|---|---|
| `sensors/group10/motorTemp/data` | `sensors/<group-id>/<project>/data` | python-device | python-edge | Raw temperature every 2 s |
| `alerts/group10/motorTemp/status` | `alerts/<group-id>/<project>/status` | python-edge | Node-RED, cloud SCADA | Z-score anomaly alert |
| `control/group10/motorTemp/fan` | `control/<group-id>/<project>/fan` | python-edge, Node-RED | python-device | Fan relay command |
| `control/group10/motorTemp/mode` | `control/<group-id>/<project>/mode` | Node-RED | python-edge | AUTO/MANUAL mode |

**Sensor payload** (`sensors/.../data`):
```json
{
  "temperature": 72.4,
  "timestamp": 1714232100.0,
  "fan_state": "OFF"
}
```

**Alert payload** (`alerts/.../status`):
```json
{
  "status": "WARNING",
  "temperature": 72.4,
  "z_score": 2.31,
  "fan_command": "ON",
  "timestamp": 1714232100.0
}
```

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

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in your InfluxDB and Grafana credentials. **Never commit `.env`.**

### 3. Start the full stack

```bash
docker compose up --build
```

All 6 services will start automatically:

| Service | URL |
|---|---|
| Node-RED Dashboard | http://localhost:1880/dashboard |
| Node-RED Editor | http://localhost:1880 |
| InfluxDB | http://localhost:8086 |
| Grafana | http://localhost:3000 |
| MQTT Broker | localhost:1883 |

### 4. Verify the pipeline

Watch the logs for activity:

```bash
# Device — temperature data publishing every 2 s
docker logs -f python-device

# Edge AI — Z-score classification
docker logs -f python-edge
```

Expected output from `python-edge`:
```
[EDGE ] temp=72.40°C  z=+2.310  status=WARNING   ai_fan=ON   mode=AUTO  window=50
```

### 5. Connecting to the lecturer's cloud broker

Edit `python/config.py` and set `CLOUD_BROKER` to the lecturer's IP:

```python
CLOUD_BROKER = "192.168.x.x"   # replace with actual IP
```

Then rebuild:

```bash
docker compose up --build python-edge
```

### 6. Swapping simulation for a real ESP32

Stop the simulated device container:
```bash
docker compose stop python-device
```

Flash your ESP32 to:
- Connect to this machine's IP on port `1883`
- Publish to `sensors/group10/motorTemp/data` every 2 seconds
- Payload: `{"temperature": <float>, "timestamp": <unix_epoch>, "fan_state": "ON"|"OFF"}`
- Subscribe to `control/group10/motorTemp/fan` and drive the relay accordingly

---

## Security Notes

> **MQTT broker authentication:** Anonymous access is enabled in `mosquitto/mosquitto.conf` (`allow_anonymous true`).
>
> **Why:** The Edge AI Python containers (`python-device`, `python-edge`) do not carry credentials, and the lecturer's spec does not require broker-level authentication. This simplifies the setup for the course environment.
>
> **To re-enable auth:** Set `allow_anonymous false` and uncomment `password_file /mosquitto/config/passwd` in `mosquitto/mosquitto.conf`. Generate the password file with: `mosquitto_passwd -c mosquitto/passwd <username>`

---

## Results

*Screenshots to be added after demo.*

---

## Challenges

- Merging two independently developed codebases (different topic namespaces, different Docker service names, different auth configs)
- Bridging the Node-RED dashboard (Dashboard v3) with the InfluxDB historian so both the HMI and digital twin views stay live from the same data source
- Z-score classification requires at least 10 readings before triggering alerts (cold-start period)

---

## Future Improvements

- Replace mock publisher with real ESP32 firmware
- Connect to lecturer's cloud SCADA broker for live demo
- Add TensorFlow Lite model for more accurate anomaly classification
- Add Remaining Useful Life (RUL) estimation panel in Grafana
- Enable MQTT TLS for production-grade security
