LOCAL_BROKER = "mqtt"          # Docker service name, used inside containers
CLOUD_BROKER = "localhost"     # Placeholder — replace with lecturer's IP later
PORT = 1883
GROUP_ID = "group10"

SENSOR_TOPIC = "sensors/group10/motorTemp/data"
ALERT_TOPIC  = "alerts/group10/motorTemp/status"
FAN_TOPIC    = "control/group10/motorTemp/fan"
MODE_TOPIC   = "control/group10/motorTemp/mode"

FAN_OFF_CONSECUTIVE_NORMAL = 5

# Temperature thresholds — used by the z_score baseline module and synthetic data generation
T_WARNING  = 85.0
T_CRITICAL = 90.0

# Active ML algorithm for fan control classification.
# Options: "z_score" | "decision_tree" | "isolation_forest" | "random_forest"
ACTIVE_ALGO = "isolation_forest"
