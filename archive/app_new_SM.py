# =====================================================
# Rover Control Panel (Flask + GPIO)
# =====================================================

from flask import Flask, render_template, request, jsonify
import RPi.GPIO as GPIO
import threading
import time
import os

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
    BPWM = 13

    GPIO.setup(AIN1, GPIO.OUT)
    GPIO.setup(AIN2, GPIO.OUT)
    GPIO.setup(APWM, GPIO.OUT)
    GPIO.setup(BIN1, GPIO.OUT)
    GPIO.setup(BIN2, GPIO.OUT)
    GPIO.setup(BPWM, GPIO.OUT)

    # PWM setup
    pwmA = GPIO.PWM(APWM, 100)
    pwmB = GPIO.PWM(BPWM, 100)
    pwmA.start(0)
    pwmB.start(0)

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

# PWM duty cycle ramping
current_duty_cycles = {'APWM': 0, 'BPWM': 0}
up_target_duty_cycles = {'APWM': 100, 'BPWM': 100}
down_target_duty_cycles = {'APWM': 0, 'BPWM': 0}
ramp_up_steps = 0.5     # 2s full ramp-up
ramp_down_steps = 0.5 # full ramp-down


def ramp_up():
    """Gradually increase PWM duty cycles."""
    global current_duty_cycles
    while True:
        all_reached = True
        for key in current_duty_cycles.keys():
            if current_duty_cycles[key] < up_target_duty_cycles[key]:
                current_duty_cycles[key] += ramp_up_steps
                print(current_duty_cycles)
                if current_duty_cycles[key] > up_target_duty_cycles[key]:
                    current_duty_cycles[key] = up_target_duty_cycles[key]
                all_reached = False
        pwmA.ChangeDutyCycle(current_duty_cycles['APWM'])
        pwmB.ChangeDutyCycle(current_duty_cycles['BPWM'])
        if all_reached:
            break
        


def ramp_down():
    """Gradually decrease PWM duty cycles."""
    global current_duty_cycles
    while True:
        all_stopped = True
        for key in current_duty_cycles.keys():
            if current_duty_cycles[key] > down_target_duty_cycles[key]:
                current_duty_cycles[key] -= ramp_down_steps
                print(current_duty_cycles)
                if current_duty_cycles[key] < down_target_duty_cycles[key]:
                    current_duty_cycles[key] = down_target_duty_cycles[key]
                all_stopped = False
        pwmA.ChangeDutyCycle(current_duty_cycles['APWM'])
        pwmB.ChangeDutyCycle(current_duty_cycles['BPWM'])
        if all_stopped:
            break
        


def mot_state(new_state):
    """Moore-style motor state machine."""
    global current_state
    if current_state != new_state:
        print(f"State change: {current_state} -> {new_state}")
        current_state = new_state

    
    if current_state == 'STOP':
#        GPIO.output(AIN1, GPIO.LOW)
#        GPIO.output(AIN2, GPIO.LOW)
#        GPIO.output(BIN1, GPIO.LOW)
#        GPIO.output(BIN2, GPIO.LOW)
        threading.Thread(target=ramp_down, daemon=True).start()
        print("STOP")
        
    elif current_state == 'FORWARD':
        GPIO.output(AIN1, GPIO.HIGH)
        GPIO.output(AIN2, GPIO.LOW)
        GPIO.output(BIN1, GPIO.LOW)
        GPIO.output(BIN2, GPIO.HIGH)
        threading.Thread(target=ramp_up, daemon=True).start()
        print("FORWARD")
        
    elif current_state == 'BACKWARD':
        GPIO.output(AIN1, GPIO.LOW)
        GPIO.output(AIN2, GPIO.HIGH)
        GPIO.output(BIN1, GPIO.HIGH)
        GPIO.output(BIN2, GPIO.LOW)
        threading.Thread(target=ramp_up, daemon=True).start()
        print("BACKWARD")
        
    elif current_state == 'LEFT':
        GPIO.output(AIN1, GPIO.HIGH)
        GPIO.output(AIN2, GPIO.LOW)
        GPIO.output(BIN1, GPIO.HIGH)
        GPIO.output(BIN2, GPIO.LOW)
        threading.Thread(target=ramp_up, daemon=True).start()
        print("LEFT")
        
    elif current_state == 'RIGHT':
        GPIO.output(AIN1, GPIO.LOW)
        GPIO.output(AIN2, GPIO.HIGH)
        GPIO.output(BIN1, GPIO.LOW)
        GPIO.output(BIN2, GPIO.HIGH)
        threading.Thread(target=ramp_up, daemon=True).start()
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


@app.route('/cleanup')
def cleanup():
    mot_state('STOP')
    GPIO.cleanup()
    return "GPIO cleaned up"


# -----------------------------------------------------
# Run Flask Server
# -----------------------------------------------------
if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8000, debug=True)
    except KeyboardInterrupt:
        mot_state('STOP')
        GPIO.cleanup()
        print("GPIO cleaned up on exit")
