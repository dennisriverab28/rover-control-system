import RPi.GPIO as GPIO
import time

# ============================
# Pin Definitions
# ============================
C1 =5        # Direction pin 1
C2 = 6        # Direction pin 2
PWM_PIN = 13   # Hardware PWM Pin (pin 13 on your module)

PWM_FREQ = 500   # N20-friendly frequency

# ============================
# GPIO Setup
# ============================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(C1, GPIO.OUT)
GPIO.setup(C2, GPIO.OUT)
GPIO.setup(PWM_PIN, GPIO.OUT)

# Create PWM object
pwm_motor = GPIO.PWM(PWM_PIN, PWM_FREQ)
pwm_motor.start(0)

# ============================
# Motor Control Functions
# ============================
def motor_forward(speed=50):
    print(f"[TEST] Motor FORWARD at {speed}%")
    GPIO.output(C1, GPIO.HIGH)
    GPIO.output(C2, GPIO.LOW)
    pwm_motor.ChangeDutyCycle(speed)

def motor_backward(speed=50):
    print(f"[TEST] Motor BACKWARD at {speed}%")
    GPIO.output(C1, GPIO.LOW)
    GPIO.output(C2, GPIO.HIGH)
    pwm_motor.ChangeDutyCycle(speed)

def motor_stop():
    print("[TEST] Motor STOP")
    GPIO.output(C1, GPIO.LOW)
    GPIO.output(C2, GPIO.LOW)
    pwm_motor.ChangeDutyCycle(0)

# ============================
# Test Routine
# ============================
try:
    print("=== N20 Balance Motor Test (C1, C2, PWM13) ===")

    motor_forward(50)
    time.sleep(10)

    motor_backward(50)
    time.sleep(10)

    motor_forward(100)
    time.sleep(10)

    motor_stop()
    time.sleep(10)

    motor_backward(10)
    time.sleep(2)

    motor_stop()
    print("=== Test Complete ===")

except KeyboardInterrupt:
    print("KeyboardInterrupt received, stopping motor.")
    motor_stop()

finally:
    pwm_motor.stop()
    GPIO.cleanup()
    print("GPIO cleanup complete.")
