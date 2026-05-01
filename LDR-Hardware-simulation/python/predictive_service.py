"""
Predictive Maintenance Service — MQTT orchestrator.

Subscribes to sensor data, runs the active predictive model on a sliding
buffer of recent readings, and publishes risk predictions to a new topic.

This service is READ-ONLY with respect to fan control — it never publishes
to the fan topic. Fan decisions remain the sole responsibility of edge_ai.py.
"""

import json
import time

import paho.mqtt.client as mqtt

from config import LOCAL_BROKER, PORT, SENSOR_TOPIC
from predictive.buffer import SlidingBuffer
from predictive.model_registry import get_predictor

PREDICT_TOPIC = "predict/group10/motorTemp/risk"
BUFFER_SIZE = 30    # 60 seconds of readings at 2 s interval

buf = SlidingBuffer(maxlen=BUFFER_SIZE)
predictor = get_predictor()


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(SENSOR_TOPIC)
        print(f"[PREDICT] Connected to broker, subscribed to {SENSOR_TOPIC}")
    else:
        print(f"[PREDICT] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        return

    temperature = data["temperature"]
    buf.append(temperature)

    result = predictor(buf)

    payload = {
        **result,
        "timestamp": data.get("timestamp", time.time()),
    }
    client.publish(PREDICT_TOPIC, json.dumps(payload))

    eta_str = f"{result['eta_minutes']}min" if result["eta_minutes"] is not None else "N/A"
    print(
        f"[PREDICT] temp={temperature:.2f}°C  "
        f"risk={result['risk_score']:.4f}  "
        f"eta={eta_str}  "
        f"model={result['model']}  "
        f"buf={len(buf)}"
    )


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="predictive-service")
client.on_connect = on_connect
client.on_message = on_message

print("[PREDICT] Starting predictive maintenance service...")
client.connect(LOCAL_BROKER, PORT, 60)
client.loop_forever()
