# Rover Control System

**Platform:** Raspberry Pi — Python + Flask  
**Hardware:** 2-wheel differential-drive rover with IMU, GPS, and L298N motor driver

---

## Overview

A Raspberry Pi-powered rover with a web-based control interface. A Flask server runs on the Pi and serves a live browser dashboard — any device on the same network can drive the rover, monitor IMU tilt data, and view GPS coordinates in real time. The rover features smooth speed ramping (acceleration/deceleration), IMU-based auto-balance mode, and systemd-compatible startup scripts.

---

## Features

| Feature | Description |
|---------|-------------|
| **Web Control UI** | Browser-based joystick interface (Flask + HTML/JS) |
| **Motor Control** | Differential-drive via L298N with GPIO PWM (1 kHz) |
| **Speed Ramping** | Threaded acceleration/deceleration for smooth movement |
| **IMU Integration** | MPU-6050 tilt/balance feedback via I2C |
| **GPS Tracking** | Background GPS thread streaming real-time coordinates |
| **Auto-Balance Mode** | Toggleable IMU-based auto-leveling |
| **Startup Scripts** | `start_rover.sh`, `stop_rover.sh`, `restart_rover.sh`, `check_rover.sh` |
| **State Machine** | Motor state machine (`FORWARD`, `BACKWARD`, `LEFT`, `RIGHT`, `STOP`) |

---

## Hardware

| Component | Detail |
|-----------|--------|
| Controller | Raspberry Pi |
| Motor Driver | L298N dual H-bridge |
| Left Motor | GPIO 23 (IN1), GPIO 24 (IN2), PWM ENA=12 |
| Right Motor | GPIO 27 (IN3), GPIO 22 (IN4), PWM ENB=13 |
| IMU | MPU-6050 (I2C) |
| GPS | UART GPS module |

---

## Project Structure

```
Rover_Control_System/
├── final_version_app.py    # Main Flask app (production version)
├── app.py                  # Earlier Flask iteration
├── app_new_SM.py           # State machine refactor version
├── fixed_threading.py      # Threading fix experiment
├── Balance.py              # IMU balancing logic (MPU-6050)
├── IMU.py                  # Raw IMU data reader
├── gps_module.py           # GPS background thread
├── test_n20.py             # N20 motor hardware test
│
├── static/
│   ├── script.js           # Frontend control logic (fetch API calls)
│   └── style.css           # Dashboard styling
├── templates/
│   └── index.html          # Web control interface
│
├── start_rover.sh          # Start Flask server (background)
├── stop_rover.sh           # Kill Flask server
├── restart_rover.sh        # Restart Flask server
├── check_rover.sh          # Check if server is running
└── README.md
```

---

## Setup & Run

### Requirements
```bash
pip install flask RPi.GPIO
```
Also requires:
- `smbus2` or `smbus` for IMU I2C
- A GPS daemon (`gpsd`) if using GPS module

### Run the Server
```bash
python final_version_app.py
```
Or use the startup scripts:
```bash
bash start_rover.sh
```

### Access the Dashboard
Open a browser on any device connected to the same network:
```
http://<raspberry-pi-ip>:5000
```

---

## How It Works

### Motor Control
GPIO pins drive an L298N H-bridge. Two PWM channels (ENA at GPIO 12, ENB at GPIO 13) at 1 kHz control left/right motor speed independently. A state machine tracks the current direction (`FORWARD`, `BACKWARD`, `LEFT`, `RIGHT`, `STOP`).

### Speed Ramping
Acceleration and deceleration run in separate threads that step PWM duty cycle by 5% every 200 ms. A `threading.Lock` protects shared speed state across threads.

### IMU Balance Mode
`Balance.py` reads the MPU-6050 via I2C and runs in a daemon thread. When auto-balance is enabled, it computes tilt angle and adjusts motor output to keep the rover level.

### Web Interface
The Flask server exposes REST endpoints (`/forward`, `/backward`, `/left`, `/right`, `/stop`, `/speed`, `/balance`). The `static/script.js` sends `fetch()` requests on button press/release, updating rover state in real time.
