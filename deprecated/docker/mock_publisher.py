import paho.mqtt.client as mqtt
import json, time, random

BROKER = "localhost"
PORT = 1883
USER = "motoradmin"
PASS = "motor2026secure"
TOPIC_BASE = "factoryA/area1/motor01"
MOTOR_ID = "motor01"

baseline = 35.0  # normal idle temperature


def generate_normal(temp_baseline):
    temp = round(random.gauss(temp_baseline + 5, 1.5), 2)
    rate = round(random.uniform(0.0, 0.15), 3)
    delta = round(temp - temp_baseline, 2)
    score = round(min(delta / 50.0, 1.0), 3)
    return temp, rate, delta, score, 0


def generate_abnormal(temp_baseline):
    temp = round(random.gauss(78, 3), 2)
    rate = round(random.uniform(0.6, 1.2), 3)
    delta = round(temp - temp_baseline, 2)
    score = round(min(delta / 50.0, 1.0), 3)
    return temp, rate, delta, score, 1


# Use callback API v2 when available to avoid deprecation warnings on paho-mqtt>=2.
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()
client.username_pw_set(USER, PASS)
client.connect(BROKER, PORT)
client.loop_start()

print("Mock temperature publisher running... Ctrl+C to stop")
cycle = 0
while True:
    cycle += 1
    if cycle % 30 == 0:
        temp, rate, delta, score, flag = generate_abnormal(baseline)
        print(f"[ABNORMAL] cycle={cycle} temp={temp}C")
    else:
        temp, rate, delta, score, flag = generate_normal(baseline)

    payload = {
        "ts": int(time.time()),
        "motor_id": MOTOR_ID,
        "temperature": temp,
        "temp_rate": rate,
        "temp_baseline": baseline,
        "temp_delta": delta,
        "anomaly_score": score,
        "anomaly_flag": flag,
        "relay_state": 1,
        "mode": "live",
        "wifi_rssi": -55,
    }

    client.publish(f"{TOPIC_BASE}/telemetry/features", json.dumps(payload))
    print(f"Published: {payload}")
    time.sleep(1)