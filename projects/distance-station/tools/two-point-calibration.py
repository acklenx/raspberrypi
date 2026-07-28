import time
from machine import Pin, I2C
from vl53l0x import VL53L0X

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
tof = VL53L0X(i2c, address=0x29)

def get_average_raw(samples=30):
    readings = []
    for _ in range(samples):
        v = tof.ping()
        if 35 < v < 2000:
            readings.append(v)
        time.sleep(0.03)
    return sum(readings) / len(readings) if readings else None

print("=== QUICK 2-POINT SENSOR CALIBRATOR ===")

# Point 1: Short
input("\n1. Place target at EXACTLY 100 mm and press ENTER...")
raw_100 = get_average_raw()
print(f"   -> Raw at 100mm: {raw_100:.1f} mm")

# Point 2: Long
input("\n2. Place target at EXACTLY 800 mm and press ENTER...")
raw_800 = get_average_raw()
print(f"   -> Raw at 800mm: {raw_800:.1f} mm")

# Calculate Slope (m) and Intercept (b) for y = mx + b
# where y is ACTUAL distance and x is RAW reading
slope = (800.0 - 100.0) / (raw_800 - raw_100)
intercept = 100.0 - (slope * raw_100)

print("\n" + "="*40)
print("CALIBRATION COMPLETE!")
print("Copy and paste these coefficients into main.py:")
print(f"SLOPE = {slope:.4f}")
print(f"OFFSET = {intercept:.2f}")
print("="*40)