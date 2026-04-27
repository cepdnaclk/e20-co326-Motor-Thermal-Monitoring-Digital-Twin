# Node-RED HMI

Node-RED flows are configured manually via the Node-RED UI at http://localhost:1880.

Do not generate flows.json. Flows will be built on the canvas and exported after the system is running.

## Suggested flow

1. **MQTT In** node — subscribe to `alerts/group10/motorTemp/status` (broker: `mqtt`, port `1883`)
2. **JSON** node — parse the incoming payload
3. **Dashboard gauges / charts** — display temperature, z-score, status, and fan state
4. **MQTT Out** node — publish to `control/group10/motorTemp/fan` for manual fan override
5. **Dashboard button** — send `{"command": "ON"}` / `{"command": "OFF"}` for manual control
