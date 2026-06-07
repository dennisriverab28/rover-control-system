import smbus
import time
import math
import RPi.GPIO as GPIO

# === CONFIG ===
DEVICE_ADDRESS = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_YOUT_H = 0x45

ACCEL_SCALE = 16384.0
GYRO_SCALE = 131.0
ALPHA = 0.98

Kp, Ki, Kd = 35.0, 0.8, 0.5
DEADBAND = 1.0

# Motor pins (L298N or similar)
IN1_PIN = 5
IN2_PIN = 6
ENA_PIN = 13  # PWM pin
PWM_FREQ = 100  # Hz (software PWM)

bus = smbus.SMBus(1)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1_PIN, GPIO.OUT)
GPIO.setup(IN2_PIN, GPIO.OUT)
GPIO.setup(ENA_PIN, GPIO.OUT)

pwm = GPIO.PWM(ENA_PIN, PWM_FREQ)
pwm.start(0)  # Start with 0% duty

# === I2C READ WITH RETRY ===
def read_word(reg, retries=3):
    for _ in range(retries):
        try:
            high = bus.read_byte_data(DEVICE_ADDRESS, reg)
            low = bus.read_byte_data(DEVICE_ADDRESS, reg + 1)
            val = (high << 8) + low
            return val if val < 0x8000 else -((65535 - val) + 1)
        except OSError:
            if _ < retries - 1:
                time.sleep(0.001)
                continue
    return 0

# === INIT MPU-6050 ===
def init_mpu6050():
    try:
        bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        print("MPU-6050 initialized.")
    except Exception as e:
        print("Failed to init MPU-6050:", e)
        exit(1)

# === MOTOR CONTROL ===
def set_motor(pwm_val):
    pwm_val = max(min(pwm_val, 100), -100)  # -100 to 100%
    if pwm_val >= 0:
        GPIO.output(IN1_PIN, GPIO.HIGH)
        GPIO.output(IN2_PIN, GPIO.LOW)
    else:
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.HIGH)
        pwm_val = -pwm_val
    pwm.ChangeDutyCycle(pwm_val)

# === MAIN ===
def main():
    init_mpu6050()
    print("Calibrating gyro... (keep still)")
    bias = sum(read_word(GYRO_YOUT_H) for _ in range(100)) / (100 * GYRO_SCALE)
    print(f"Gyro bias: {bias:.3f} °/s")
    set_motor(0)

    # Initial pitch
    ax = read_word(ACCEL_XOUT_H) / ACCEL_SCALE
    ay = read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
    az = read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE
    pitch = math.degrees(math.atan2(-ax, math.sqrt(ay**2 + az**2)))

    integral = 0.0
    prev_error = 0.0
    prev_time = time.time()

    print("Balancing Y-axis with RPi.GPIO (Ctrl+C to stop)")

    try:
        while True:
            t = time.time()
            dt = t - prev_time
            if dt <= 0:
                time.sleep(0.001)
                continue
            prev_time = t

            # Read sensors
            ax = read_word(ACCEL_XOUT_H) / ACCEL_SCALE
            ay = read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
            az = read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE
            gy_raw = read_word(GYRO_YOUT_H) / GYRO_SCALE
            gy = gy_raw - bias

            if ax == 0 and ay == 0 and az == 0:  # I2C failed
                print("I2C read failed, skipping frame...")
                time.sleep(0.01)
                continue

            # Complementary filter
            accel_pitch = math.degrees(math.atan2(-ax, math.sqrt(ay**2 + az**2)))
            pitch = ALPHA * (pitch + gy * dt) + (1 - ALPHA) * accel_pitch

            # PID
            error = -pitch
            if abs(error) < DEADBAND:
                error = 0.0
                integral = 0.0
            integral += error * dt
            integral = max(min(integral, 100), -100)
            derivative = (error - prev_error) / dt
            output = Kp * error + Ki * integral + Kd * derivative
            prev_error = error

            # Scale output to -100..100%
            pwm_out = output / 3  # Adjust this scalar to tune max speed
            set_motor(pwm_out)

            if int(t * 5) % 1 == 0:
                print(f"Pitch: {pitch:6.2f}° | PWM: {pwm_out:6.1f}%")

            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        set_motor(0)
        pwm.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()

