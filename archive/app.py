# =====================================================
# Rover Control Panel (Flask + GPIO)
# =====================================================

from flask import Flask, render_template, request, jsonify
import RPi.GPIO as GPIO
import threading
import time
import os
from enum import Enum

# -----------------------------------------------------
# Flask Setup
# -----------------------------------------------------
app = Flask(__name__)

# -----------------------------------------------------
# GPIO Setup (only once)
# -----------------------------------------------------
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not hasattr(GPIO, '_initialized'):
    GPIO.setmode(GPIO.BCM)          # Use BCM numbering
    GPIO.setwarnings(False)
    # pwm pin setup

    # Left Motor Pins
    AIN1 = 23
    AIN2 = 24
    APWM = 12
    # Right Motor Pins
    BIN1 = 27
    BIN2 = 17
    BPWM = 13  
    # Setup outputs
    GPIO.setup(AIN1, GPIO.OUT)
    GPIO.setup(AIN2, GPIO.OUT)
    GPIO.setup(APWM, GPIO.OUT)
    GPIO.setup(BIN1, GPIO.OUT)
    GPIO.setup(BIN2, GPIO.OUT)
    GPIO.setup(BPWM, GPIO.OUT) 
    # Mark GPIO as initialized to avoid double setup
    GPIO._initialized = True


# -----------------------------------------------------
# Motor Control Functions
# -----------------------------------------------------
# motor controll moore state machine

current_duty_cycles = {
    'APWM': 0,
    'BPWM': 0
}
up_target_duty_cycles = {
    'APWM': 100,
    'BPWM': 100
}
down_target_duty_cycles = {
    'APWM': 0,
    'BPWM': 0
}
ramp_up_steps = 100 / (2.0 / 0.05)  # 2 seconds to full speed
ramp_down_steps = 100 / (1.0 / 0.05)  # 1 second to stop

def ramp_up():
    global current_duty_cycles, up_target_duty_cycles
    while True:
        for key in current_duty_cycles.keys():
            if current_duty_cycles[key] < up_target_duty_cycles[key]:
                current_duty_cycles[key] += ramp_up_steps
                if current_duty_cycles[key] > up_target_duty_cycles[key]:
                    current_duty_cycles[key] = up_target_duty_cycles[key]
                GPIO.PWM(APWM if key == 'APWM' else BPWM, current_duty_cycles[key])
        time.sleep(0.05)

def ramp_down():
    global current_duty_cycles, down_target_duty_cycles
    while True:
        for key in current_duty_cycles.keys():
            if current_duty_cycles[key] > down_target_duty_cycles[key]:
                current_duty_cycles[key] -= ramp_down_steps
                if current_duty_cycles[key] < down_target_duty_cycles[key]:
                    current_duty_cycles[key] = down_target_duty_cycles[key]
                GPIO.PWM(APWM if key == 'APWM' else BPWM, current_duty_cycles[key])
        time.sleep(0.05)

states = {
    'STOP': 'STOP',
    'FORWARD': 'FORWARD',
    'BACKWARD': 'BACKWARD',
    'LEFT': 'LEFT',
    'RIGHT': 'RIGHT'
}



current_state = states['STOP']

def mot_state(states):
    global current_state
    if current_state != states:
        current_state = states
        print(f"State changed to: {current_state}")
    
    match current_state:
        case 'STOP':
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.LOW)
            GPIO.output(BIN1, GPIO.LOW)
            GPIO.output(BIN2, GPIO.LOW)
            ramp_down()
            print("STOP")
            
        case 'FORWARD':
            GPIO.output(AIN1, GPIO.HIGH)
            GPIO.output(AIN2, GPIO.LOW)
            GPIO.output(BIN1, GPIO.LOW)
            GPIO.output(BIN2, GPIO.HIGH)
            ramp_up()
            print("FORWARD")
            
        case 'BACKWARD':
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.HIGH)
            GPIO.output(BIN1, GPIO.HIGH)
            GPIO.output(BIN2, GPIO.LOW)
            ramp_up()
            print("BACKWARD")
            
        case 'LEFT':
            GPIO.output(AIN1, GPIO.HIGH)
            GPIO.output(AIN2, GPIO.LOW)
            GPIO.output(BIN1, GPIO.HIGH)
            GPIO.output(BIN2, GPIO.LOW)
            ramp_up()
            print("LEFT")
            
        case 'RIGHT':
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.HIGH)
            GPIO.output(BIN1, GPIO.LOW)
            GPIO.output(BIN2, GPIO.HIGH)
            ramp_up()
            print("RIGHT")
            
# -----------------------------------------------------
# Motor Control Functions  
# -----------------------------------------------------
#def stop():
#    GPIO.output(AIN1, GPIO.LOW)
#    GPIO.output(AIN2, GPIO.LOW)
#    GPIO.output(BIN1, GPIO.LOW)
#    GPIO.output(BIN2, GPIO.LOW)
#    print("STOP")
#
#def move_forward():
#    GPIO.output(AIN1, GPIO.HIGH)
#    GPIO.output(AIN2, GPIO.LOW)
#    GPIO.output(BIN1, GPIO.LOW)
#    GPIO.output(BIN2, GPIO.HIGH)
#   print("FORWARD")
#
#def move_backward():
#    GPIO.output(AIN1, GPIO.LOW)
#    GPIO.output(AIN2, GPIO.HIGH)
#    GPIO.output(BIN1, GPIO.HIGH)
#    GPIO.output(BIN2, GPIO.LOW)
#    print("BACKWARD")
#
#def turn_left():
#    GPIO.output(AIN1, GPIO.HIGH)
#    GPIO.output(AIN2, GPIO.LOW)
#   GPIO.output(BIN1, GPIO.HIGH)
#    GPIO.output(BIN2, GPIO.LOW)
#    print("LEFT")
#
#def turn_right():
#    GPIO.output(AIN1, GPIO.LOW)
#   GPIO.output(AIN2, GPIO.HIGH)
#    GPIO.output(BIN1, GPIO.LOW)
#    GPIO.output(BIN2, GPIO.HIGH)
#    print("RIGHT")


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
        current_state ='FORWARD'
        print("Forward")
    elif direction == 'backward':
        current_state = states['BACKWARD']
    elif direction == 'left':
        current_state = states['LEFT']
    elif direction == 'right':
        current_state = states['RIGHT']
    elif direction == 'stop':
        current_state = states['STOP']
    else:
        print("Invalid command")

    return jsonify({'status': 'ok', 'command': direction})


# -----------------------------------------------------
# Clean Up
# -----------------------------------------------------
@app.route('/cleanup')
def cleanup():
    current_state = 'STOP'
    GPIO.cleanup()
    return "GPIO cleaned up"


# -----------------------------------------------------
# Run Flask Server
# -----------------------------------------------------
if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8000, debug=True)
        mot_states()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("GPIO cleaned up on exit")
