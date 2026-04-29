#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ── User configuration ─────────────────────────────────────────────
// const char* WIFI_SSID     = "Lahiru - Dialog 4G";
// const char* WIFI_PASSWORD = "12345@109876";
const char* WIFI_SSID     = "Haritha";
const char* WIFI_PASSWORD = "ifnb2124";
const char* MQTT_SERVER   = "10.244.91.208";
const int   MQTT_PORT     = 1883;
// ──────────────────────────────────────────────────────────────────

const char* SENSOR_TOPIC = "sensors/group10/motorTemp/data";
const char* FAN_TOPIC    = "control/group10/motorTemp/fan";
const char* CLIENT_ID    = "esp32-group10";

const int LDR_PIN   = 34;  // ADC1 — works while WiFi is active (GPIO 13 = ADC2, disabled by WiFi)
const int RELAY_PIN = 12;  // HIGH = ON, LOW = OFF (active-HIGH relay module)

bool fanState = false;
unsigned long lastPublish = 0;
const unsigned long PUBLISH_INTERVAL = 2000;

WiFiClient   espClient;
PubSubClient mqttClient(espClient);


void connectWiFi() {
  Serial.print("[DEVICE] Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("[DEVICE] WiFi connected — IP: ");
  Serial.println(WiFi.localIP());
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[DEVICE] Connecting to MQTT...");
    if (mqttClient.connect(CLIENT_ID)) {
      Serial.println(" connected.");
      mqttClient.subscribe(FAN_TOPIC);
    } else {
      Serial.printf(" failed (rc=%d), retrying in 3 s\n", mqttClient.state());
      delay(3000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, FAN_TOPIC) != 0) return;

  StaticJsonDocument<64> doc;
  if (deserializeJson(doc, payload, length)) return;

  const char* cmd = doc["command"];
  if (!cmd) return;

  fanState = (strcmp(cmd, "ON") == 0);
  digitalWrite(RELAY_PIN, fanState ? HIGH : LOW);
  Serial.printf("[DEVICE] Fan → %s\n", fanState ? "ON" : "OFF");
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);   // fan OFF at startup (active-HIGH relay: LOW = de-energised)

  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqttClient.connected())        connectMQTT();
  mqttClient.loop();  // runs every iteration — fan commands handled within milliseconds

  unsigned long now = millis();
  if (now - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = now;

    int   ldrValue   = analogRead(LDR_PIN);
    float temperature = 40.0f + ((float)ldrValue / 4095.0f) * 60.0f;

    StaticJsonDocument<128> doc;
    doc["temperature"] = roundf(temperature * 100.0f) / 100.0f;
    doc["timestamp"]   = now / 1000.0f;
    doc["fan_state"]   = fanState ? "ON" : "OFF";

    char payload[128];
    serializeJson(doc, payload);
    mqttClient.publish(SENSOR_TOPIC, payload);

    Serial.printf("[DEVICE] ldr=%4d  temp=%.2f°C  fan=%s\n",
                  ldrValue, temperature, fanState ? "ON" : "OFF");
  }
}
