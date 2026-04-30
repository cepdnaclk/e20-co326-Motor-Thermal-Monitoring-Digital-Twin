# ESP32 Firmware — PlatformIO Setup & Flash Guide

This guide covers setting up PlatformIO, configuring the firmware for your
network, and flashing it to the ESP32 dev board used in this project.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| VS Code | [code.visualstudio.com](https://code.visualstudio.com) |
| PlatformIO IDE extension | Install from VS Code Extensions panel |
| USB cable | Data cable (not charge-only) |
| CP2102 / CH340 driver | Usually auto-installed; see [Troubleshooting](#troubleshooting) if the port is not detected |

> PlatformIO handles the ESP32 toolchain, board support, and library
> downloads automatically — no manual SDK installation needed.

---

## 1. Install PlatformIO

1. Open VS Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Search for **PlatformIO IDE** and click **Install**.
4. Wait for the install to finish, then **restart VS Code** when prompted.

You should now see the PlatformIO ant icon in the left sidebar.

---

## 2. Create the PlatformIO Project

### Option A — Open the existing firmware folder (recommended)

1. Click the PlatformIO icon → **Open** → **Open Project**.
2. Navigate to `LDR-Hardware-simulation/firmware/` and open it.
3. If PlatformIO does not detect a project (no `platformio.ini`), choose
   **Option B** instead.

### Option B — Create a new project and copy the firmware

1. Click the PlatformIO icon → **Open** → **New Project**.
2. Fill in the wizard:
   - **Name:** `motor-thermal-ldr`
   - **Board:** `Espressif ESP32 Dev Module`
   - **Framework:** `Arduino`
   - **Location:** choose a folder (or leave default)
3. Click **Finish** and wait for the toolchain to download (~2 min on first run).
4. Copy `firmware/firmware.ino` into the project's `src/` folder and rename it
   `main.cpp`.

> PlatformIO uses `src/main.cpp`; Arduino IDE uses `.ino`. The code is
> identical — only the extension and location differ.

---

## 3. Configure `platformio.ini`

Open `platformio.ini` in the project root and replace its contents with:

```ini
[env:esp32dev]
platform  = espressif32
board     = esp32dev
framework = arduino

; Serial monitor baud rate — must match Serial.begin(115200) in firmware
monitor_speed = 115200

; Upload speed — reduce to 460800 if you get frequent upload errors
upload_speed = 921600

; Libraries — PlatformIO fetches these automatically
lib_deps =
    knolleary/PubSubClient @ ^2.8
    bblanchon/ArduinoJson  @ ^6.21
```

Save the file. PlatformIO will fetch the two libraries the next time you build.

---

## 4. Edit the Firmware Configuration

Open `src/main.cpp` (or `firmware.ino`) and update the three constants at the
top of the file:

```cpp
// ── User configuration ─────────────────────────────────────────────
const char* WIFI_SSID     = "your-network-name";
const char* WIFI_PASSWORD = "your-password";
const char* MQTT_SERVER   = "192.168.x.x";   // ← host machine LAN IP
const int   MQTT_PORT     = 1883;
// ──────────────────────────────────────────────────────────────────
```

### Finding the host machine IP

The ESP32 connects to the MQTT broker running on your PC inside Docker.
Run the appropriate command on the host machine:

| OS | Command |
|---|---|
| Windows | `ipconfig` → look for **IPv4 Address** under your Wi-Fi adapter |
| Linux / macOS | `ip addr` or `ifconfig` → look for `inet` on your Wi-Fi interface |

Use the LAN IP (e.g. `192.168.1.42`), **not** `localhost` or `127.0.0.1` —
the ESP32 is a separate device on the network.

> Both the ESP32 and the host machine must be on the **same Wi-Fi network**.
> The Docker MQTT broker must be running (`docker-compose up`) before the
> ESP32 tries to connect.

---

## 5. Hardware Wiring

Verify your wiring matches the pin assignments in the firmware before flashing.

```
ESP32 Dev Module
│
├── GPIO 34 (ADC1)  ──── LDR voltage divider midpoint
│                             LDR ── midpoint ── 10 kΩ resistor ── GND
│                             3V3 ──────────────────────────────────┘
│
├── GPIO 12         ──── Relay module IN pin
│
├── 3V3             ──── Relay module VCC
├── GND             ──── Relay module GND
│
├── 3V3             ──── LDR one end
└── GND             ──── 10 kΩ resistor other end
```

**Relay wiring note:** the relay module used is **active-HIGH**
(`HIGH` = energised = fan ON). The firmware drives GPIO 12 HIGH to turn the
fan on and LOW to turn it off. If your relay module is active-LOW, swap the
`HIGH`/`LOW` values in `mqttCallback()`.

**ADC note:** GPIO 34 is on ADC1, which remains functional while Wi-Fi is
active. Do **not** move the LDR to GPIO 13 (ADC2) — ADC2 is disabled by the
Wi-Fi driver on ESP32.

---

## 6. Build the Firmware

In VS Code with PlatformIO:

- Click the **Build** button (✓ tick) in the PlatformIO toolbar at the bottom, or
- Open the PlatformIO sidebar → **PROJECT TASKS** → `esp32dev` → **Build**, or
- Use the keyboard shortcut: `Ctrl+Alt+B`

A successful build ends with:

```
================================ [SUCCESS] ================================
RAM:   [=         ]  10.2% (used 33484 bytes from 327680 bytes)
Flash: [===       ]  29.4% (used 386058 bytes from 1310720 bytes)
```

Fix any compilation errors before proceeding to flash.

---

## 7. Connect the ESP32

1. Plug the ESP32 into your PC via the USB cable.
2. The port should appear automatically. Verify it in PlatformIO:
   - PlatformIO sidebar → **Devices** — you should see something like
     `COM3` (Windows) or `/dev/ttyUSB0` (Linux).
3. If no port appears, see [Troubleshooting](#troubleshooting).

---

## 8. Flash the Firmware

- Click the **Upload** button (→ arrow) in the PlatformIO toolbar, or
- PlatformIO sidebar → `esp32dev` → **Upload**, or
- Keyboard shortcut: `Ctrl+Alt+U`

PlatformIO will compile (if not already built) and then flash. Watch the
output panel:

```
Connecting........_____....
Chip is ESP32-D0WD-V3 (revision v3.1)
...
Writing at 0x00010000... (100 %)
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```

> If the upload stalls at `Connecting.......` hold the **BOOT** button on the
> ESP32 board until the upload starts, then release it.

---

## 9. Verify with Serial Monitor

Open the Serial Monitor immediately after flashing:

- Click the **Serial Monitor** button (plug icon) in the PlatformIO toolbar, or
- PlatformIO sidebar → `esp32dev` → **Monitor**, or
- Keyboard shortcut: `Ctrl+Alt+S`

Baud rate is set to **115200** in `platformio.ini` (`monitor_speed`).

Expected startup output:

```
[DEVICE] Connecting to WiFi.....
[DEVICE] WiFi connected — IP: 192.168.1.77
[DEVICE] Connecting to MQTT... connected.
[DEVICE] ldr= 812  temp=51.90°C  fan=OFF
[DEVICE] ldr= 819  temp=51.99°C  fan=OFF
```

Cover the LDR with your hand — the `temp` value should rise toward 95–100 °C.

If you see `failed (rc=-2), retrying in 3 s`, the ESP32 cannot reach the MQTT
broker. Double-check `MQTT_SERVER`, ensure Docker is running, and confirm both
devices are on the same network.

---

## 10. Confirm End-to-End

With the Docker stack running (`docker-compose up`) and the ESP32 flashed:

1. Open the Node-RED dashboard at `http://localhost:1880/dashboard`.
2. The **Temperature Gauge** and **Chart** should update every 2 seconds.
3. Cover the LDR → temperature rises → edge AI triggers WARNING / CRITICAL →
   fan relay activates → **Fan Status** on dashboard shows spinning fan.
4. Uncover → readings return to baseline → after 5 consecutive NORMAL
   readings, fan turns OFF.

---

## MQTT Topics Published / Subscribed by the ESP32

| Topic | Direction | Payload example |
|---|---|---|
| `sensors/group10/motorTemp/data` | ESP32 → broker | `{"temperature":72.4,"timestamp":12.3,"fan_state":"OFF"}` |
| `control/group10/motorTemp/fan` | broker → ESP32 | `{"command":"ON"}` |

---

## Troubleshooting

### Port not detected

- **Windows:** Install the CP2102 driver from Silicon Labs or the CH340 driver
  from WCH. Unplug and replug after installing.
- **Linux:** Add your user to the `dialout` group:
  ```bash
  sudo usermod -aG dialout $USER
  ```
  Log out and back in, then replug.
- Try a different USB cable — many cables are charge-only with no data lines.

### Upload stalls at `Connecting.......`

Hold the **BOOT** (or **IO0**) button on the ESP32 board until the upload
progress bar starts, then release. Some boards require this if auto-reset is
not wired.

### `rc=-2` — MQTT connection refused / broker unreachable

- Confirm `MQTT_SERVER` is the host machine's LAN IP, not `localhost`.
- Confirm the Docker stack is running: `docker-compose ps` should show the
  `mqtt` service as `Up`.
- Confirm the ESP32 is on the same Wi-Fi network as the host machine.
- Check that port 1883 is not blocked by the host firewall:
  ```bash
  # Windows (run as administrator)
  netsh advfirewall firewall add rule name="MQTT" protocol=TCP dir=in localport=1883 action=allow
  ```

### Temperature reads 40 °C constantly (LDR always at 0)

- Verify the LDR is wired to **GPIO 34**, not GPIO 13 or another ADC2 pin.
- Check the voltage divider: the midpoint should float between ~0.5 V (bright)
  and ~2.5 V (covered) when measured with a multimeter.

### Relay does not activate

- Verify the relay IN pin is connected to **GPIO 12**.
- Confirm the relay module is powered (3V3 or 5V depending on your module).
- If the relay triggers when it should be off (inverted logic), your module is
  active-LOW. Swap `HIGH`/`LOW` in `mqttCallback()` in the firmware.
