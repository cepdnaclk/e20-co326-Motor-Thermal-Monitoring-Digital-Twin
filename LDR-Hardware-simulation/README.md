# Motor Thermal Monitoring Digital Twin — LDR Hardware

An Edge AI Industrial IoT system for real-time anomaly detection using an ESP32 with an LDR sensor, MQTT, Docker, and Node-RED.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  DEVICE LAYER (ESP32)                                           │
│  LDR sensor + relay-controlled fan                             │
│  Maps LDR reading to temperature, publishes every 2 s          │
│  Publishes: sensors/group10/motorTemp/data                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MQTT (local broker, port 1883)
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

## Hardware

| Component | GPIO |
|---|---|
| LDR (voltage divider, LDR on GND side) | GPIO 13 (analog in) |
| Relay module (HIGH = OFF, LOW = ON) | GPIO 12 (digital out) |

**LDR orientation:** covering the LDR increases its resistance, raising the midpoint voltage and producing a **higher ADC reading**. The firmware maps higher readings to higher temperatures — covering the LDR simulates a motor overheating.

---

## MQTT Topics

| Topic | Publisher | Subscriber | Purpose |
|---|---|---|---|
| `sensors/group10/motorTemp/data` | ESP32 | python-edge | LDR-mapped temperature readings (2 s interval) |
| `alerts/group10/motorTemp/status` | python-edge | Node-RED, cloud SCADA | Processed anomaly alerts with z-score |
| `control/group10/motorTemp/fan` | python-edge, Node-RED | ESP32 | Fan relay command (ON / OFF) |
| `control/group10/motorTemp/mode` | Node-RED | python-edge | AUTO / MANUAL mode (retained) |

---

## How to Run

### 1. Flash the ESP32

1. Open `firmware/motor_temp_ldr.ino` in Arduino IDE
2. Install libraries via **Tools → Manage Libraries**:
   - `PubSubClient` by Nick O'Leary
   - `ArduinoJson` by Benoit Blanchon
3. Edit the three constants at the top of the sketch:
   ```cpp
   const char* WIFI_SSID     = "your-network-name";
   const char* WIFI_PASSWORD = "your-password";
   const char* MQTT_SERVER   = "192.168.x.x";  // host machine LAN IP
   ```
   Find the host IP with `ip addr` (Linux) or `ipconfig` (Windows).
4. Select **Board: ESP32 Dev Module**, choose the correct port, and flash.

### 2. Start the Docker stack

```bash
docker-compose up --build
```

- Node-RED dashboard: http://localhost:1880/dashboard
- MQTT broker: localhost:1883

### 3. Test

- Cover the LDR with your hand → temperature reading rises → edge AI triggers WARNING / CRITICAL → relay activates fan
- Uncover → readings return to baseline → after 5 consecutive NORMAL readings, fan turns OFF

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
