import smbus
import time
import math
import pigpio

# I2C address of the MPU-6050
DEVICE_ADDRESS = 0x68

# MPU-6050 Registers
PWR_MGMT_1 = 0x6B
GYRO_YOUT_H = 0x45
ACCEL_XOUT_H = 0x3B

# Gyro sensitivity scale factor (default: +/- 250 deg/s)
GYRO_SCALE = 131.0  # LSB/(deg/s)
ACCEL_SCALE = 16384.0

ALPHA = 0.98

Kp = 35.0
Ki = 0.8
Kd = 0.5

IN1_PIN = 5
IN2_PIN = 6
PWM_PIN = 13
PWM_FREQ = 25000
MAX_PWM = 255
DEADBAND = 1.0

bus = smbus.SMBus(1)
pi = pigpio.pi()

def read_word(reg):
    high = bus.read_byte_data(DEVICE_ADDRESS, reg)
    low = bus.read_byte_data(DEVICE_ADDRESS, reg + 1)
    val = (high << 8) + low
    if val >= 0x8000:  # Two's complement
        val = -((65535 - val) + 1)
    return val

def init_mpu6050():
    bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0x00)
    time.sleep(0.1)
    print("MPU-6050 initialized.")

def set_motor(pwm):
    pwm = max(min(pwm, MAX_PWM), -MAX_PWM)
    if pwm >= 0:
        pi.write(IN1_PIN, 1)
        pi.write(IN2_PIN, 0)
    else:
        pi.write(IN1_PIN, 0)
        pi.write(IN2_PIN, 1)

    duty = int(pwm / MAX_PWM * 1000000)
    duty = max(0, min(duty, 1000000))
    pi.hardware_PWM(PWM_PIN, PWM_FREQ, duty)

def main():
    init_mpu6050()

    pi.set_mode(IN1_PIN, pigpio.OUTPUT)
    pi.set_mode(IN2_PIN, pigpio.OUTPUT)
    pi.set_mode(PWM_PIN, pigpio.OUTPUT)
    set_motor(0)
    # Initialize I2C bus (use 1 for Raspberry Pi 2 and later)
    accel_x = read_word(ACCEL_XOUT_H) / ACCEL_SCALE
    accel_y = read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
    accel_z = read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE
    pitch = math.degrees(math.atan2(-accel_x, math.sqrt(accel_y**2 + accel_z**2)))
    
    integral = 0.0
    prev_error = 0.0
    prev_time = time.time()
    
    print("Starting Y-axis balancing (Ctrl+C to stop)")
    print("Tune PID if needed: Kp=%.1f, Ki=%.1f, Kd=%.1f" % (Kp, Ki, Kd))
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            if dt <= 0:
                time.sleep(0.001)
                continue
            prev_time = current_time
            
            # Read raw data
            accel_x = read_word(ACCEL_XOUT_H) / ACCEL_SCALE
            accel_y = read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
            accel_z = read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE
            gyro_y = read_word(GYRO_YOUT_H) / GYRO_SCALE
            
            # Accel-based pitch
            accel_pitch = math.degrees(math.atan2(-accel_x, math.sqrt(accel_y**2 + accel_z**2)))
            
            # Complementary filter
            pitch = ALPHA * (pitch + gyro_y * dt) + (1 - ALPHA) * accel_pitch
            
            # PID
            error = -pitch  # Target: 0°
            if abs(error) < DEADBAND:
                error = 0.0
                integral = 0.0  # Reset integral in deadband
            integral += error * dt
            derivative = (error - prev_error) / dt
            output = Kp * error + Ki * integral + Kd * derivative
            prev_error = error
            
            # Drive motor
            set_motor(int(output))
            
            # Print every 0.2s
            if current_time % 0.2 < dt:
                print(f"Pitch: {pitch:6.2f}° | Error: {error:6.2f}° | PWM: {output:5.0f}")
            
            time.sleep(0.005)  # ~200 Hz loop
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        set_motor(0)
        pi.stop()

if __name__ == "__main__":
    main()
