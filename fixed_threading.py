# =====================================================
# Rover Control Panel (Flask + GPIO)
# =====================================================

from flask import Flask, render_template, request, jsonify
import RPi.GPIO as GPIO
import psutil
import socket
import threading
import time
import os
import Balance
import gps_module
gps_module.start_gps()


# Ensure Flask can always find templates/static no matter where it's launched
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static')
)
# -----------------------------------------------------
# Flask Setup
# -----------------------------------------------------
app = Flask(__name__)

# -----------------------------------------------------
# GPIO Setup (only once)
# -----------------------------------------------------
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not hasattr(GPIO, '_initialized'):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Left Motor Pins
    AIN1 = 23
    AIN2 = 24
    APWM = 12
    # Right Motor Pins
    BIN1 = 27
    BIN2 = 17
   # BPWM = 13

    # Setup outputs
    GPIO.setup(AIN1, GPIO.OUT)
    GPIO.setup(AIN2, GPIO.OUT)
    GPIO.setup(APWM, GPIO.OUT)
    GPIO.setup(BIN1, GPIO.OUT)
    GPIO.setup(BIN2, GPIO.OUT)
  #  GPIO.setup(BPWM, GPIO.OUT)

    # Initialize PWM at 1 kHz
    pwmA = GPIO.PWM(APWM, 1000)
 #   pwmB = GPIO.PWM(BPWM, 1000)
    pwmA.start(0)
 #   pwmB.start(0)

    GPIO._initialized = True


# -----------------------------------------------------
# Motor Control State Machine
# -----------------------------------------------------

states = {
    'STOP': 'STOP',
    'FORWARD': 'FORWARD',
    'BACKWARD': 'BACKWARD',
    'LEFT': 'LEFT',
    'RIGHT': 'RIGHT'
}

current_state = states['STOP']
accel_thread_running = False
stop_event = threading.Event()

# Shared duty cycle
current_speed = 0  # percentage 0–100
speed_lock = threading.Lock()

# -----------------------------------------------------
# Speed Ramping Threads
# -----------------------------------------------------

def accelerate(direction):
    """Gradually accelerate while in given direction."""
    global current_speed, accel_thread_running
    accel_thread_running = True
    stop_event.clear()

    print(f"Starting acceleration for {direction}...")

    while not stop_event.is_set() and current_state == direction:
        with speed_lock:
            if current_speed < 100:
                current_speed += 10  # increase by 5% each step
                if current_speed > 100:
                    current_speed = 100
            pwmA.ChangeDutyCycle(current_speed)
 #           pwmB.ChangeDutyCycle(current_speed)
            print(f"Duty: {current_speed}%")  # optional debug
        time.sleep(0.05)

    accel_thread_running = False
    print(f"Acceleration thread for {direction} ended.")


def decelerate():
    """Gradually slow down both motors to stop."""
    global current_speed, accel_thread_running
    accel_thread_running = True
    stop_event.set()  # signal acceleration thread to stop

    print("Starting deceleration...")

    while current_speed > 0:
        with speed_lock:
            current_speed -= 10
            if current_speed < 0:
                current_speed = 0
            pwmA.ChangeDutyCycle(current_speed)
 #           pwmB.ChangeDutyCycle(current_speed)
        print(f"Duty: {current_speed}%")
        time.sleep(0.05)

    accel_thread_running = False
    print("Deceleration complete. Motors stopped.")


# -----------------------------------------------------
# State Machine Logic
# -----------------------------------------------------

def mot_state(new_state):
    """Main motor control state machine."""
    global current_state, accel_thread_running

    # Prevent re-triggering same state
    if current_state == new_state:
        return

    print(f"State change: {current_state} -> {new_state}")
    current_state = new_state

    match current_state:
        case 'STOP':
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.LOW)
            GPIO.output(BIN1, GPIO.LOW)
            GPIO.output(BIN2, GPIO.LOW)
#            if not accel_thread_running:
            threading.Thread(target=decelerate, daemon=True).start()
            print("STOP")

        case 'FORWARD':
            GPIO.output(AIN1, GPIO.HIGH)
            GPIO.output(AIN2, GPIO.LOW)
            GPIO.output(BIN1, GPIO.LOW)
            GPIO.output(BIN2, GPIO.HIGH)
            if not accel_thread_running:
                threading.Thread(target=accelerate, args=('FORWARD',), daemon=True).start()
            print("FORWARD")

        case 'BACKWARD':
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.HIGH)
            GPIO.output(BIN1, GPIO.HIGH)
            GPIO.output(BIN2, GPIO.LOW)
            if not accel_thread_running:
                threading.Thread(target=accelerate, args=('BACKWARD',), daemon=True).start()
            print("BACKWARD")

        case 'LEFT':
            GPIO.output(AIN1, GPIO.HIGH)
            GPIO.output(AIN2, GPIO.LOW)
            GPIO.output(BIN1, GPIO.HIGH)
            GPIO.output(BIN2, GPIO.LOW)
            if not accel_thread_running:
                threading.Thread(target=accelerate, args=('LEFT',), daemon=True).start()
            print("LEFT")

        case 'RIGHT':
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.HIGH)
            GPIO.output(BIN1, GPIO.LOW)
            GPIO.output(BIN2, GPIO.HIGH)
            if not accel_thread_running:
                threading.Thread(target=accelerate, args=('RIGHT',), daemon=True).start()
            print("RIGHT")


# -----------------------------------------------------
# Web Routes
# -----------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/move', methods=['POST'])
def move():
    direction = request.json['command']

    if direction == 'forward':
        mot_state('FORWARD')
    elif direction == 'backward':
        mot_state('BACKWARD')
    elif direction == 'left':
        mot_state('LEFT')
    elif direction == 'right':
        mot_state('RIGHT')
    elif direction == 'stop':
        mot_state('STOP')
    else:
        print("Invalid command")

    return jsonify({'status': 'ok', 'command': direction})
# -----------------------------------------------------
# System Control Routes
# -----------------------------------------------------
@app.route('/status')
def status():
    # CPU and system stats
    cpu_temp = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            cpu_temp = round(int(f.read()) / 1000, 1)
    except:
        cpu_temp = "N/A"

    cpu_usage = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime_seconds = time.time() - psutil.boot_time()
    uptime = time.strftime("%Hh %Mm", time.gmtime(uptime_seconds))

    # Network info
    try:
        ip_address = socket.gethostbyname(socket.gethostname())
    except:
        ip_address = "N/A"

    # Check if camera port 8889 open
    cam_status = "Closed"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    result = sock.connect_ex(("localhost", 8889))
    if result == 0:
        cam_status = "Open"
    sock.close()

    return jsonify({
        "CPU Temp": f"{cpu_temp}°C",
        "CPU Usage": f"{cpu_usage}%",
        "RAM Usage": f"{mem.percent}%",
        "Disk Usage": f"{disk.percent}%",
        "Uptime": uptime,
        "IP Address": ip_address,
        "Camera Port": f"8889 ({cam_status})"
    })


@app.route('/reboot', methods=['POST'])
def reboot_pi():
    os.system("sudo reboot")
    return jsonify({"message": "Rebooting Raspberry Pi..."})


@app.route('/shutdown', methods=['POST'])
def shutdown_pi():
    os.system("sudo shutdown now")
    return jsonify({"message": "Shutting down Raspberry Pi..."})


##CLEANUP

@app.route('/cleanup')
def cleanup():
    mot_state('STOP')
    GPIO.cleanup()
    return "GPIO cleaned up"
#------------------------------------------------------
#Run the gps commands here
#------------------------------------------------------
@app.route('/gps')
def gps_status():
    return jsonify(gps_module.get_data())

@app.route('/ping')
def ping_location():
    data = gps_module.get_data()
    print(f"[PING] Location: {data}")
    return jsonify({"message": "Pinged!", "gps_data": data})

# -----------------------------------------------------
# Run Flask Server
# -----------------------------------------------------
if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
        Balance.main()
    except KeyboardInterrupt:
        mot_state('STOP')
        GPIO.cleanup()
        print("GPIO cleaned up on exit")
