import RPi.GPIO as GPIO
import time
import threading
from flask import Flask, render_template, request, jsonify
import gps_module
import Balance  # IMU + balancing logic

# ============================
# GPIO Setup
# ============================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ============================
# Motor Pin Definitions
# ============================
# Left Motor
IN1 = 23
IN2 = 24
ENA = 12  # PWM

# Right Motor
IN3 = 27
IN4 = 22
ENB = 13  # PWM

# Setup GPIO pins
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

# Initialize PWM at 1000Hz (ONLY ONCE)
pwm_left = GPIO.PWM(ENA, 1000)
pwm_right = GPIO.PWM(ENB, 1000)
pwm_left.start(0)
pwm_right.start(0)
print("[INIT] PWM objects created on ENA=12 and ENB=13")

# ============================
# Global State and Locks
# ============================
mot_current_state = 'STOP'
direction_state = 'STOP'
current_speed = 0
target_speed = 0
stop_flag = False

speed_lock = threading.Lock()
balance_thread = None  # Thread handler for IMU-based auto-balancing

# Flags to manage speed ramping behavior
acceleration_thread = None
deceleration_thread = None

# Start GPS background thread (already implemented in gps_module)
print("[INIT] Starting GPS background thread from gps_module")
gps_module.start_gps()

app = Flask(__name__)


# ============================
# Low-Level Motor Control
# ============================
def set_motor_pins(left_forward, left_backward, right_forward, right_backward):
    GPIO.output(IN1, GPIO.HIGH if left_forward else GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH if left_backward else GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH if right_forward else GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH if right_backward else GPIO.LOW)


def set_motor_speed(speed):
    """Set PWM duty cycle for both motors."""
    global current_speed

    # Safety: if PWM somehow didn't initialize, don't crash
    if pwm_left is None or pwm_right is None:
        print("[MOTOR] WARNING: PWM not initialized, skipping speed change")
        return

    with speed_lock:
        current_speed = speed

    pwm_left.ChangeDutyCycle(speed)
    pwm_right.ChangeDutyCycle(speed)
    print(f"[MOTOR] PWM speed set to: {speed}%")


def mot_state(state):
    """Update motor state and apply direction pins."""
    global mot_current_state, stop_flag

    stop_flag = (state == 'STOP')
    mot_current_state = state
    print(f"[STATE] Motor state changed to: {mot_current_state}")

    if state == 'FORWARD':
        set_motor_pins(True, False, True, False)
    elif state == 'BACKWARD':
        set_motor_pins(False, True, False, True)
    elif state == 'LEFT':
        set_motor_pins(False, True, True, False)
    elif state == 'RIGHT':
        set_motor_pins(True, False, False, True)
    elif state == 'STOP':
        set_motor_pins(False, False, False, False)
        set_motor_speed(0)


# ============================
# IMU / Balance Thread
# ============================

def start_balance_thread():
    """Start the IMU balancing loop in a background thread."""
    global balance_thread

    # If it's already running, don't start another copy
    if balance_thread is not None and balance_thread.is_alive():
        print("[BALANCE] Balance thread already running")
        return

    def _balance_worker():
        print("[BALANCE] Balance thread starting (IMU + auto-level active)")
        try:
            # Your Balance.main() should internally loop, read the IMU,
            # and either just log angles or adjust a *separate* motor.
            Balance.main()
        except Exception as e:
            print(f"[BALANCE] Balance thread error: {e}")
        finally:
            print("[BALANCE] Balance thread stopped")

    balance_thread = threading.Thread(target=_balance_worker, daemon=True)
    balance_thread.start()
    print("[BALANCE] Balance thread launched")


# ============================
# Speed Ramping Threads
# ============================

def accelerate():
    """Gradually increase speed from current_speed up to target_speed."""
    global current_speed, target_speed, stop_flag

    print("[SPEED] Acceleration thread started")
    while not stop_flag:
        with speed_lock:
            if current_speed >= target_speed:
                break
            current_speed += 5
            if current_speed > target_speed:
                current_speed = target_speed
            speed = current_speed

        set_motor_speed(speed)
        time.sleep(0.2)

    print(f"[SPEED] Acceleration thread ended at speed {current_speed}")


def decelerate():
    """Gradually decrease speed from current_speed down to 0."""
    global current_speed, target_speed, stop_flag

    print("[SPEED] Deceleration thread started")
    while True:
        with speed_lock:
            # If we've been told to STOP, ramp down to 0
            if current_speed <= 0:
                current_speed = 0
                set_motor_speed(0)
                break
            current_speed -= 5
            if current_speed < 0:
                current_speed = 0
            speed = current_speed

        set_motor_speed(speed)
        time.sleep(0.2)

    print("[SPEED] Deceleration thread ended, speed is 0")


def start_acceleration():
    global acceleration_thread, deceleration_thread, stop_flag

    stop_flag = False
    if deceleration_thread and deceleration_thread.is_alive():
        print("[SPEED] Waiting for deceleration thread to finish before accelerating")
        deceleration_thread.join()

    if not acceleration_thread or not acceleration_thread.is_alive():
        print("[SPEED] Launching new acceleration thread")
        acceleration_thread = threading.Thread(target=accelerate, daemon=True)
        acceleration_thread.start()


def start_deceleration():
    global deceleration_thread, acceleration_thread, stop_flag

    stop_flag = True
    if acceleration_thread and acceleration_thread.is_alive():
        print("[SPEED] Waiting for acceleration thread to finish before decelerating")
        acceleration_thread.join()

    if not deceleration_thread or not deceleration_thread.is_alive():
        print("[SPEED] Launching new deceleration thread")
        deceleration_thread = threading.Thread(target=decelerate, daemon=True)
        deceleration_thread.start()


# ============================
# Flask Routes
# ============================

@app.route('/')
def index():
    print("[HTTP] GET / -> index.html")
    return render_template('index.html')


@app.route('/move', methods=['POST'])
def move():
    global direction_state, target_speed
    data = request.json
    direction = data.get('direction', '').upper()

    print(f"[HTTP] /move with direction='{direction}'")

    if direction == 'FORWARD':
        direction_state = 'FORWARD'
        target_speed = 80  # Tune as needed
        mot_state(direction_state)
        start_acceleration()

    elif direction == 'BACKWARD':
        direction_state = 'BACKWARD'
        target_speed = 80
        mot_state(direction_state)
        start_acceleration()

    elif direction == 'LEFT':
        direction_state = 'LEFT'
        target_speed = 60  # Slightly lower for turning
        mot_state(direction_state)
        start_acceleration()

    elif direction == 'RIGHT':
        direction_state = 'RIGHT'
        target_speed = 60
        mot_state(direction_state)
        start_acceleration()

    elif direction == 'STOP':
        direction_state = 'STOP'
        mot_state('STOP')
        start_deceleration()

    else:
        print(f"[WARN] Unknown direction requested: {direction}")
        return jsonify({'status': 'error', 'message': 'Invalid direction'}), 400

    return jsonify({'status': 'ok', 'direction': direction_state, 'speed': current_speed})


@app.route('/status', methods=['GET'])
def status():
    gps_data = gps_module.get_data()
    response = {
        'motor_state': mot_current_state,
        'direction_state': direction_state,
        'current_speed': current_speed,
        'gps': gps_data
    }
    print(f"[HTTP] /status -> {response}")
    return jsonify(response)


@app.route('/ping', methods=['GET'])
def ping():
    gps_data = gps_module.get_data()
    motor_status = {
        'motor_state': mot_current_state,
        'direction_state': direction_state,
        'current_speed': current_speed
    }
    combined = {
        'status': 'running',
        'gps': gps_data,
        'motor': motor_status
    }
    print(f"[HTTP] /ping -> {combined}")
    return jsonify(combined)


# ============================
# Cleanup on Exit
# ============================
def cleanup():
    print("[CLEANUP] Stopping motors and cleaning up GPIO")
    try:
        mot_state('STOP')
    except Exception as e:
        print(f"[CLEANUP] Error while stopping motors: {e}")
    try:
        GPIO.cleanup()
    except Exception as e:
        print(f"[CLEANUP] Error during GPIO.cleanup(): {e}")
    print("[CLEANUP] GPIO cleaned up")


# ============================
# Main Entry Point
# ============================
if __name__ == '__main__':
    try:
        print("[MAIN] Starting IMU balance background thread")
        start_balance_thread()

        print("[MAIN] Starting Flask web server on 0.0.0.0:8000")
        app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

    except KeyboardInterrupt:
        print("[MAIN] KeyboardInterrupt received")

    except Exception as e:
        print(f"[MAIN] Unhandled exception: {e}")

    finally:
        cleanup()

