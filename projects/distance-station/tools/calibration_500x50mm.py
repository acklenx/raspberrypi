import time
from machine import Pin, I2C
from vl53l0x import VL53L0X

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
tof = VL53L0X(i2c, address=0x29)

# Sweep every 50 mm from 400 mm up to 1000 mm
long_range_targets = list(range(400, 1050, 50))

print("--- Long Range Diagnostic Sweep (400 mm - 1000 mm) ---")

for target in long_range_targets:
    input(f"\nPlace target at EXACTLY {target} mm and press ENTER...")
    
    samples = []
    for _ in range(25):
        val = tof.ping()
        # Accept valid ToF returns (8190 is hardware timeout)
        if 35 < val < 2000:
            samples.append(val)
        time.sleep(0.04)
    
    if samples:
        avg_raw = sum(samples) / len(samples)
        delta = avg_raw - target
        print(f"Target: {target:>4d} mm | Raw Avg: {avg_raw:>6.1f} mm | Delta: {delta:>+6.1f} mm")
    else:
        print(f"Target: {target:>4d} mm | NO VALID READINGS (Timeout or out of range)")