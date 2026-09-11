"""Does turning on the RealSense kill the fingers?

The fingers and the D435i share one physical VIA Labs hub: fingers on its USB2 half
(1-4.3, 1-4.4), the camera on its USB3 half (2-4.1). The camera draws 720 mA against
the fingers' 100 mA each. This runs the fingers alone for a baseline, then starts the
camera mid-soak at a known instant and keeps going, so a death can be timed against
the camera rather than against anything else.

No CAN, no arms, no other cameras, no encoding.

  python rs_soak.py [baseline_s] [total_s]
"""

import sys
import time

import numpy as np

from lerobot.cameras.realsense.camera_realsense import RealSenseCamera
from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig
from sensible_finger.array import TactileArray
from sensible_finger.config import FingerConfig, TactileConfig

BASELINE = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
TOTAL = float(sys.argv[2]) if len(sys.argv) > 2 else 900.0
SIDES = ["right_finger", "left_finger"]
FPS = 30
SERIAL = "327122076093"

arr = TactileArray(TactileConfig(fingers=[FingerConfig(side=s) for s in SIDES], backend="real"))
arr.connect(tare=False)
if arr.missing:
    print(f"MISSING {sorted(arr.missing)}")
    raise SystemExit(1)

print("pre-flight ...", flush=True)
alive, warm = {s: 0 for s in SIDES}, {s: None for s in SIDES}
t_pre = time.monotonic()
while time.monotonic() - t_pre < 2.5:
    r = arr.read()
    for s in SIDES:
        v = r[s].raw
        if warm[s] is not None and not np.array_equal(v, warm[s]):
            alive[s] += 1
        warm[s] = v.copy()
    time.sleep(1 / FPS)
for s in SIDES:
    print(f"  {s:13s} {alive[s]:3d}/75 moved -> {'alive' if alive[s] >= 20 else 'FROZEN'}", flush=True)
if any(alive[s] < 20 for s in SIDES):
    print("\nABORTING: replug the frozen finger(s) first.\n")
    arr.disconnect()
    raise SystemExit(2)

print(f"\nphase 1: fingers alone for {BASELINE:.0f}s, camera OFF", flush=True)
print(f"phase 2: RealSense {SERIAL} 848x480x30 with depth, until t={TOTAL:.0f}s\n", flush=True)
print(f"  {'t(s)':>6} {'cam':>4}  {'right peak':>18}  {'left peak':>18}", flush=True)

cam = None
cam_on_at = None
prev = {s: None for s in SIDES}
sec_moved = {s: 0 for s in SIDES}
dead = {s: None for s in SIDES}
n = 0
t0 = time.monotonic()
last_report = -1.0

while (t := time.monotonic() - t0) < TOTAL:
    tick = time.monotonic()

    if cam is None and t >= BASELINE:
        print(f"\n  >>> t={t:.1f}s  STARTING REALSENSE\n", flush=True)
        cam = RealSenseCamera(RealSenseCameraConfig(
            serial_number_or_name=SERIAL, width=848, height=480, fps=30, use_depth=True))
        cam.connect()
        cam_on_at = time.monotonic() - t0
        print(f"  >>> t={time.monotonic() - t0:.1f}s  REALSENSE STREAMING\n", flush=True)

    reads = arr.read()
    n += 1
    for s in SIDES:
        v = reads[s].raw
        if prev[s] is not None and not np.array_equal(v, prev[s]):
            sec_moved[s] += 1
        prev[s] = v.copy()

    if cam is not None:
        try:
            cam.async_read(timeout_ms=200)
        except Exception:
            try:
                cam.read()
            except Exception as e:
                print(f"  camera read failed: {e}", flush=True)

    if t - last_report >= 1.0:
        last_report = t
        row = f"  {t:6.1f} {'ON' if cam else 'off':>4}  "
        for s in SIDES:
            pk = float(prev[s].max())
            # valid (status[3]) distinguishes an MCU hang from a yanked cable. Both make
            # frozen_s climb identically, because the reader holds its last value either
            # way, so printing frozen_s alone will have you debugging the wrong thing.
            ok = float(reads[s].status[3]) > 0.5
            row += (f"{pk:8.0f} mv{sec_moved[s]:3d} f{float(reads[s].status[4]):4.1f} "
                    f"{'ok' if ok else 'GONE':>4}  ")
            sec_moved[s] = 0
        print(row, flush=True)
        for s in SIDES:
            if dead[s] is None and float(reads[s].status[4]) >= 2.0:
                dead[s] = t
                since = "camera was never started" if cam_on_at is None else \
                    f"{t - cam_on_at:.1f}s AFTER the RealSense started"
                if float(reads[s].status[3]) > 0.5:
                    kind = "FROZE (MCU hang, USB link still up)"
                else:
                    kind = ("LOST ITS USB LINK (valid=0). This is NOT a freeze. "
                            "Check dmesg -T for a disconnect before concluding anything.")
                print(f"\n  >>> {s} {kind} at t={t:.1f}s   ({since})\n", flush=True)

    if all(d is not None for d in dead.values()):
        print("  both dead, stopping\n", flush=True)
        break

    dt = time.monotonic() - tick
    if dt < 1 / FPS:
        time.sleep(1 / FPS - dt)

print("=" * 78)
print(f"  RealSense started at t={cam_on_at:.1f}s" if cam_on_at else "  RealSense never started")
for s in SIDES:
    print(f"  {s:13s} died at {f'{dead[s]:.1f}s' if dead[s] is not None else 'NEVER (survived)'}")
print("=" * 78)
if cam is not None:
    cam.disconnect()
arr.disconnect()
