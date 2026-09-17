"""Do the fingers freeze on their own, with no cameras and no CAN?

Mirrors the record loop's access pattern exactly: both fingers through one
TactileArray, drained at 30 Hz. Nothing else runs. If they freeze here, the
device is at fault on its own. If they survive, the trigger is something the
record run adds (USB bandwidth from three cameras, CPU load, or power).
"""
import sys, time
import numpy as np
from sensible_finger.array import TactileArray
from sensible_finger.config import FingerConfig, TactileConfig

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0
SIDES = sys.argv[2].split(",") if len(sys.argv) > 2 else ["right_finger", "left_finger"]
FPS = 30

arr = TactileArray(TactileConfig(fingers=[FingerConfig(side=s) for s in SIDES], backend="real"))
arr.connect(tare=False)          # no tare: a stuck finger tares "successfully" at p2p 0
if arr.missing:
    print(f"MISSING {sorted(arr.missing)}"); raise SystemExit(1)

# Pre-flight. A finger still hung from an earlier run reads as perfectly healthy on
# every signal except frozen_s, so without this the whole soak measures nothing.
print("pre-flight: checking both fingers are actually alive ...", flush=True)
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
    print("\nABORTING: replug the frozen finger(s) first. Nothing in software clears it.\n")
    arr.disconnect()
    raise SystemExit(2)

prev = {s: None for s in SIDES}
changed = {s: 0 for s in SIDES}
froze_at = {s: None for s in SIDES}
n = 0
t0 = time.monotonic()
print(f"\nsoaking both fingers at {FPS} Hz for {DURATION:.0f}s, untouched\n", flush=True)

while (t := time.monotonic() - t0) < DURATION:
    tick = time.monotonic()
    reads = arr.read()
    n += 1
    for s in SIDES:
        v = reads[s].raw
        if prev[s] is not None and not np.array_equal(v, prev[s]):
            changed[s] += 1
        prev[s] = v.copy()
        if froze_at[s] is None and reads[s].status[4] >= 2.0:
            froze_at[s] = t
            # valid (status[3]) separates an MCU hang from a yanked cable. Both hold
            # the last value and so climb frozen_s identically; only this tells them
            # apart, and a link drop means go read dmesg rather than blame the device.
            if float(reads[s].status[3]) <= 0.5:
                print(f"\n  >>> {s} LOST ITS USB LINK (valid=0) at t={t:.1f}s. NOT a freeze. "
                      f"Check dmesg -T for a disconnect.\n", flush=True)
            else:
                print(f"\n  >>> {s} FROZE at t={t:.1f}s (MCU hang, USB link still up)\n", flush=True)
    if n % (FPS * 15) == 0:
        cols = "   ".join(
            f"{s:13s} moved {changed[s]:5d}/{n}  frozen_s {reads[s].status[4]:5.1f}  "
            f"{'ok' if float(reads[s].status[3]) > 0.5 else 'GONE'}" for s in SIDES
        )
        print(f"  t={t:6.1f}s   {cols}", flush=True)
    dt = time.monotonic() - tick
    if dt < 1 / FPS:
        time.sleep(1 / FPS - dt)

print("\n" + "=" * 70)
for s in SIDES:
    r = arr.reader(s)
    print(f"  {s:13s} moved {changed[s]}/{n} frames   "
          f"dropped {getattr(r, 'dropped', '?')}   push_errors {getattr(r, 'push_errors', '?')}   "
          f"froze at {f'{froze_at[s]:.1f}s' if froze_at[s] is not None else 'never'}")
print("=" * 70)
arr.disconnect()
