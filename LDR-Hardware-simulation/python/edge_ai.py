import importlib
import json
import time
from collections import deque

import paho.mqtt.client as mqtt

from config import (
    LOCAL_BROKER, CLOUD_BROKER, PORT,
    SENSOR_TOPIC, ALERT_TOPIC, FAN_TOPIC, MODE_TOPIC,
    FAN_OFF_CONSECUTIVE_NORMAL, ACTIVE_ALGO,
)

_VALID_ALGOS = {"z_score", "decision_tree", "isolation_forest", "random_forest"}
if ACTIVE_ALGO not in _VALID_ALGOS:
    raise ValueError(f"config.ACTIVE_ALGO={ACTIVE_ALGO!r} is not valid. Choose from: {_VALID_ALGOS}")

_algo_mod  = importlib.import_module(f"ml.{ACTIVE_ALGO}")
classify   = _algo_mod.classify
load_model = _algo_mod.load_model
print(f"[EDGE ] Algorithm: {ACTIVE_ALGO}")

WINDOW_SIZE = 50

window = deque(maxlen=WINDOW_SIZE)
consecutive_normal = 0
current_fan_command = "OFF"
current_mode = "AUTO"

load_model()

local_client = mqtt.Client(client_id="edge-local")
cloud_client = mqtt.Client(client_id="edge-cloud")


def on_message(client, userdata, msg):
    global consecutive_normal, current_fan_command

    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        return

    temperature = data["temperature"]
    window.append(temperature)

    status, score = classify(temperature, window)

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
        "z_score": round(score, 4),
        "fan_command": current_fan_command,
        "timestamp": data.get("timestamp", time.time()),
    })
    local_client.publish(ALERT_TOPIC, alert_payload)
    try:
        cloud_client.publish(ALERT_TOPIC, alert_payload)
    except Exception:
        pass

    print(
        f"[EDGE ] temp={temperature:.2f}°C  score={score:+.3f}  "
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
