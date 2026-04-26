# Motor Thermal Monitoring Digital Twin

An Edge AI Industrial IoT system for real-time motor temperature anomaly detection using MQTT, Docker, and Node-RED.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  DEVICE LAYER (python-device container / real ESP32)            │
│  Simulates motor + temperature sensor + fan relay               │
│  Publishes: sensors/group10/motorTemp/data  (every 2 s)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MQTT (local broker)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  EDGE AI LAYER (python-edge container)                          │
│  Z-score anomaly detection on rolling 50-reading window         │
│  Fan control with hysteresis                                    │
│  Publishes alerts locally and to cloud SCADA broker             │
└────────┬──────────────────────────────────────┬─────────────────┘
         │ MQTT (local broker)                  │ MQTT (cloud broker)
         ▼                                      ▼
┌─────────────────────────┐         ┌───────────────────────────┐
│  HMI LAYER (Node-RED)   │         │  SCADA LAYER              │
│  Dashboard at :1880     │         │  Lecturer's cloud broker   │
│  Real-time monitoring   │         │  Receives alerts only      │
│  Manual fan override    │         │  (never raw sensor data)   │
└─────────────────────────┘         └───────────────────────────┘
```

---

## MQTT Topics

| Topic | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `sensors/group10/motorTemp/data` | python-device | python-edge | Raw temperature readings (2 s interval) |
| `alerts/group10/motorTemp/status` | python-edge | Node-RED, cloud SCADA | Processed anomaly alerts with z-score |
| `control/group10/motorTemp/fan` | python-edge, Node-RED | python-device | Fan relay command (ON / OFF) |

---

## How to Run

```bash
docker-compose up --build
```

- Node-RED dashboard: http://localhost:1880
- MQTT broker: localhost:1883

Build the Node-RED dashboard by connecting **MQTT In** → **JSON** → dashboard widgets as described in [node-red/README.md](node-red/README.md).

---

## Swapping Simulation for a Real ESP32

1. Stop the simulated device container:
   ```bash
   docker-compose stop python-device
   ```
2. Flash your ESP32 with firmware that:
   - Connects to this machine's IP on port **1883**
   - Publishes to `sensors/group10/motorTemp/data` every 2 seconds  
     Payload: `{"temperature": <float>, "timestamp": <unix_epoch>, "fan_state": "ON"|"OFF"}`
   - Subscribes to `control/group10/motorTemp/fan` and drives the relay accordingly

No other changes to the system are required.

---

## Connecting to the Cloud SCADA Broker

Edit [python/config.py](python/config.py) and set `CLOUD_BROKER` to the lecturer's IP:

```python
CLOUD_BROKER = "192.168.x.x"   # replace with actual IP
```

Then rebuild:

```bash
docker-compose up --build python-edge
```

---

## Group Members

| Name | Index |
|---|---|
| (placeholder) | (placeholder) |
| (placeholder) | (placeholder) |
| (placeholder) | (placeholder) |

---

## Challenges

- (placeholder)

---

## Future Improvements

- (placeholder)
