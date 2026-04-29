import json
import time
from collections import deque

import numpy as np
import paho.mqtt.client as mqtt

from config import (
    LOCAL_BROKER, CLOUD_BROKER, PORT,
    SENSOR_TOPIC, ALERT_TOPIC, FAN_TOPIC, MODE_TOPIC,
    FAN_OFF_CONSECUTIVE_NORMAL,
)

WINDOW_SIZE = 50
MIN_READINGS = 10

# Absolute thresholds tuned for LDR hardware:
# uncovered baseline ≈ 77-79°C, fully covered ≈ 95°C
T_WARNING  = 85.0
T_CRITICAL = 90.0

window = deque(maxlen=WINDOW_SIZE)
consecutive_normal = 0
current_fan_command = "OFF"
current_mode = "AUTO"

local_client = mqtt.Client(client_id="edge-local")
cloud_client = mqtt.Client(client_id="edge-cloud")


def classify(temperature):
    # Compute z-score for reporting even though classification uses absolute thresholds
    z = 0.0
    if len(window) >= MIN_READINGS:
        arr = np.array(window)
        mean, std = arr.mean(), arr.std()
        if std > 0:
            z = (temperature - mean) / std

    if temperature > T_CRITICAL:
        return "CRITICAL", z
    if temperature > T_WARNING:
        return "WARNING", z
    return "NORMAL", z


def on_message(client, userdata, msg):
    global consecutive_normal, current_fan_command

    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        return

    temperature = data["temperature"]
    window.append(temperature)

    status, z_score = classify(temperature)

    if status in ("WARNING", "CRITICAL"):
        current_fan_command = "ON"
        consecutive_normal = 0
    else:
        consecutive_normal += 1
        if consecutive_normal >= FAN_OFF_CONSECUTIVE_NORMAL:
            current_fan_command = "OFF"

    if current_mode == "AUTO":
        fan_payload = json.dumps({"command": current_fan_command})
        local_client.publish(FAN_TOPIC, fan_payload)

    alert_payload = json.dumps({
        "status": status,
        "temperature": temperature,
        "z_score": round(z_score, 4),
        "fan_command": current_fan_command,
        "timestamp": data.get("timestamp", time.time()),
    })
    local_client.publish(ALERT_TOPIC, alert_payload)
    try:
        cloud_client.publish(ALERT_TOPIC, alert_payload)
    except Exception:
        pass

    print(
        f"[EDGE ] temp={temperature:.2f}°C  z={z_score:+.3f}  "
        f"status={status:<8}  ai_fan={current_fan_command}  "
        f"mode={current_mode}  window={len(window)}"
    )


def on_mode_message(client, userdata, msg):
    global current_mode
    try:
        current_mode = json.loads(msg.payload.decode())["mode"]
        print(f"[EDGE ] Mode changed to {current_mode}")
    except Exception:
        pass


local_client.on_message = on_message
local_client.message_callback_add(MODE_TOPIC, on_mode_message)
local_client.connect(LOCAL_BROKER, PORT, 60)
local_client.subscribe(SENSOR_TOPIC)
local_client.subscribe(MODE_TOPIC)

try:
    cloud_client.connect(CLOUD_BROKER, PORT, 60)
    cloud_client.loop_start()
    print("[EDGE ] Cloud broker connected.")
except Exception as e:
    print(f"[EDGE ] Cloud broker unavailable ({e}). Continuing without cloud.")

local_client.loop_forever()
