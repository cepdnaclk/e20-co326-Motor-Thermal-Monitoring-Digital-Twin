# Deprecated — Rollback Reference

This folder preserves old code versions for rollback purposes. **Do not run anything from here directly.**

---

## `deprecated/docker/`

**What it was:** Janith's original infrastructure stack.

Contains:
- `docker-compose.yml` — 4 services: Mosquitto (with password auth), Node-RED, InfluxDB 2.7, Grafana
- `config/mosquitto.conf` — Mosquitto with `allow_anonymous false` + password file
- `mock_publisher.py` — Simple Python script to simulate ESP32 telemetry (no Edge AI)
- `.env` — Live credentials (gitignored)

**Why superseded:**
- Used a non-standard topic (`factoryA/area1/motor01/...`) not matching the lecturer's `sensors/<group-id>/<project>/data` format
- No Edge AI layer (only threshold-based alarm in Node-RED)
- Python script was not containerized, so it ran outside Docker
- Mosquitto password auth was incompatible with the teammate's Python containers

---

## `deprecated/code-v2/`

**What it was:** Teammate's initial implementation with Edge AI.

Contains:
- `python/mqtt_publisher.py` — Simulated motor device (publishes to `sensors/group10/motorTemp/data`)
- `python/edge_ai.py` — Z-score anomaly detection with fan control and cloud SCADA bridge
- `python/config.py` — Topics and broker config
- `python/Dockerfile` — Python container build
- `node-red/flows.json` — Node-RED Dashboard v3 (chart, gauge, alert log, fan controls, mode switch)
- `docker-compose.yml` — 4 services: mqtt, node-red, python-device, python-edge (no InfluxDB/Grafana)
- `mosquitto/mosquitto.conf` — Anonymous broker

**Why superseded:**
- Missing InfluxDB and Grafana (no historian, no digital twin dashboard)
- MQTT broker service name was `mqtt`; merged system standardizes on `mosquitto`

---

*Merged into the root project structure on 2026-04-27.*
