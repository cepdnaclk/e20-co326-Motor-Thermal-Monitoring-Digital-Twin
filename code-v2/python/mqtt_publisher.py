import json
import math
import random
import time

import paho.mqtt.client as mqtt

from config import LOCAL_BROKER, PORT, SENSOR_TOPIC, FAN_TOPIC

fan_state = "OFF"
cooling_offset = 0.0


def on_connect(client, userdata, flags, rc):
    client.subscribe(FAN_TOPIC)


def on_message(client, userdata, msg):
    global fan_state
    try:
        payload = json.loads(msg.payload.decode())
        fan_state = payload.get("command", fan_state)
    except Exception:
        pass


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(LOCAL_BROKER, PORT, 60)
client.loop_start()

t = 0
while True:
    r = random.random()
    if r < 0.10:
        anomaly = random.uniform(10, 20)   # CRITICAL spike
    elif r < 0.25:
        anomaly = random.uniform(4, 7)     # WARNING spike
    else:
        anomaly = 0.0
    noise = random.uniform(-0.5, 0.5)
    base_temp = 65 + 3 * math.sin(t / 20) + noise + anomaly

    if fan_state == "ON":
        cooling_offset = min(cooling_offset + 0.3, base_temp - 65)
    else:
        cooling_offset = max(cooling_offset - 0.1, 0.0)

    temperature = base_temp - cooling_offset

    payload = {
        "temperature": round(temperature, 2),
        "timestamp": time.time(),
        "fan_state": fan_state,
    }
    client.publish(SENSOR_TOPIC, json.dumps(payload))
    tier = "CRITICAL" if anomaly >= 10 else "WARNING" if anomaly > 0 else "none"
    print(f"[DEVICE] temp={temperature:.2f}°C  fan={fan_state}  anomaly={tier}")

    t += 1
    time.sleep(2)
