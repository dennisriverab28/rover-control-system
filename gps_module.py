# gps_module.py
import serial
import pynmea2
import threading
import time

gps_data = {
    "latitude": None,
    "longitude": None,
    "altitude": None,
    "fix": "No Fix",
    "satellites": 0
}

def read_gps():
    """Continuously read GPS data from /dev/ttyAMA0"""
    global gps_data
    try:
        with serial.Serial('/dev/ttyAMA0', 9600, timeout=1) as ser:
            while True:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$GPGGA'):
                    try:
                        msg = pynmea2.parse(line)
                        gps_data["latitude"] = msg.latitude
                        gps_data["longitude"] = msg.longitude
                        gps_data["altitude"] = msg.altitude
                        gps_data["fix"] = "3D Fix" if msg.gps_qual > 0 else "No Fix"
                        gps_data["satellites"] = msg.num_sats
                    except pynmea2.ParseError:
                        continue
    except serial.SerialException as e:
        print(f"[GPS] Serial error: {e}")
    except Exception as e:
        print(f"[GPS] Unexpected error: {e}")

def start_gps():
    """Start the GPS reader thread"""
    gps_thread = threading.Thread(target=read_gps, daemon=True)
    gps_thread.start()

def get_data():
    """Return the latest GPS data dictionary"""
    return gps_data
