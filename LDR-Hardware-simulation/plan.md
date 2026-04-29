# Plan: LDR Hardware Simulation — ESP32 Firmware + Docker Adjustments

## Context
The software-simulation folder uses `mqtt_publisher.py` to fake a motor sensor.
The LDR-Hardware-simulation folder is a copy of that, but the device layer will now
be a real ESP32 with an LDR + relay wired to GPIO 13 / GPIO 12.

**Hardware orientation:** LDR is the bottom leg of the voltage divider (connected to GND side).
Covering the LDR increases its resistance → raises the midpoint voltage → **higher ADC reading**.
- **Uncovered (bright):** ldrValue < 3000 → normal, lower temperature
- **Covered (dark):** ldrValue > 3000 → anomaly, higher temperature

The ESP32 replaces the Python device container entirely. The rest of the stack
(Mosquitto, Node-RED, edge_ai.py) stays the same because the MQTT topic/payload
contract is unchanged.

---

## What changes (LDR-Hardware-simulation only)

### 1. CREATE `firmware/motor_temp_ldr.ino`
Arduino sketch for ESP32. Libraries required: `WiFi.h` (built-in), `PubSubClient`, `ArduinoJson`.

**Pin layout (matches existing hardware):**
- `LDR_PIN  = 13` (analog in)
- `RELAY_PIN = 12` (digital out, HIGH = OFF, LOW = ON)

**LDR → temperature mapping (linear, full ADC range):**
```
temperature = 40.0 + (ldrValue / 4095.0) * 60.0
```
- ldrValue = 0   (max light, uncovered): 40 °C
- ldrValue = 3000 (threshold):           ~84 °C — but z-score adapts to baseline, not absolute value
- ldrValue = 4095 (max dark, covered):  100 °C

Because z-score is relative to the rolling window baseline, the absolute values don't need to match
the old simulation. What matters is that covering the LDR produces readings significantly above
the uncovered baseline, which this mapping guarantees.

Payload format kept **identical** to software-simulation:
`{"temperature": float, "timestamp": float, "fan_state": "ON"|"OFF"}`

**Behaviour:**
- Connect to WiFi (`WIFI_SSID` / `WIFI_PASSWORD` constants — user must fill in)
- Connect to MQTT broker at `MQTT_SERVER` (host machine LAN IP — user must fill in;
  Docker "mqtt" service name is not reachable from WiFi)
- Publish to `sensors/group10/motorTemp/data` every 2 s
- Subscribe to `control/group10/motorTemp/fan` → parse `{"command":"ON"|"OFF"}` → drive relay
- Reconnect loop for both WiFi and MQTT
- Serial log at 115200 baud

Port 1883 is already exposed from Docker compose — no change needed there.

---

### 2. MODIFY `docker-compose.yml`
Remove the `python-device` service. Keep: `mqtt`, `node-red`, `python-edge`.
No other compose changes needed.

---

### 3. MODIFY `README.md`
- Update device-layer description to reflect real ESP32 with LDR + relay
- Add firmware flashing instructions:
  1. Install PubSubClient and ArduinoJson in Arduino IDE Library Manager
  2. Open `firmware/motor_temp_ldr.ino`
  3. Set `WIFI_SSID`, `WIFI_PASSWORD`, `MQTT_SERVER` (host machine LAN IP)
  4. Select board: ESP32 Dev Module, flash
- Remove the "how to swap simulation for ESP32" section (now it IS the default)

---

### 4. CREATE `LDR-Hardware-simulation/plan.md`
Write the full contents of this plan file into `plan.md` at the project root.

---

## What does NOT change

| File | Reason |
|---|---|
| `python/edge_ai.py` | Z-score is scale-invariant; adapts to whatever baseline the LDR produces; payload format identical |
| `python/config.py` | Topics, broker names, and constants are all unchanged |
| `python/Dockerfile` | Still valid; python-edge is the only Python container now |
| `mosquitto/mosquitto.conf` | Unchanged |
| `python/mqtt_publisher.py` | Not deleted — kept as fallback reference. Removed from docker-compose only |
| `node-red/flows.json` | Dashboard subscribes to same topics; no changes needed |

---

## Verification

1. Flash ESP32 with firmware (fill in SSID/IP constants first)
2. `docker-compose up --build` (python-device service is gone; only python-edge rebuilds)
3. Cover LDR with hand → ADC reading rises above baseline → edge logs show WARNING/CRITICAL → relay activates
4. Uncover LDR → readings return to baseline → after 5 consecutive NORMAL readings, fan turns OFF
5. Node-RED dashboard shows live temperature, status changes, fan state
