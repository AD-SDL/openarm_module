"""Does force kill the fingers, or do they die on their own?

Same access pattern as the record loop, no cameras and no CAN. Prints load once a
second so a deliberate press shows up in the trace, and on death dumps the five
seconds of load history leading up to it. If a finger dies within a second or two of
a press, force is the trigger. If it dies untouched, it is not.

  python press_soak.py [duration_s] [right_finger,left_finger]
"""

import sys
import time
from collections import deque

import numpy as np

from sensible_finger.array import TactileArray
from sensible_finger.config import FingerConfig, TactileConfig

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
SIDES = sys.argv[2].split(",") if len(sys.argv) > 2 else ["right_finger", "left_finger"]
FPS = 30

arr = TactileArray(TactileConfig(fingers=[FingerConfig(side=s) for s in SIDES], backend="real"))
arr.connect(tare=False)  # no tare: a stuck finger tares "successfully" at p2p 0
if arr.missing:
    print(f"MISSING {sorted(arr.missing)}")
    raise SystemExit(1)

# Pre-flight. A finger that is already hung from a previous run will sit there
# looking healthy and burn the whole soak, so refuse to start on a dead one.
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
    verdict = "alive" if alive[s] >= 20 else "FROZEN"
    print(f"  {s:13s} {alive[s]:3d}/75 frames moved  ->  {verdict}"
          f"{'   stuck at peak ' + str(int(warm[s].max())) if alive[s] < 20 else ''}", flush=True)
if any(alive[s] < 20 for s in SIDES):
    print("\nABORTING: unplug and replug the frozen finger(s), then run this again.")
    print("Nothing in software clears this state, so the soak would measure nothing.\n")
    arr.disconnect()
    raise SystemExit(2)
print("both alive, starting soak\n", flush=True)

prev = {s: None for s in SIDES}
changed = {s: 0 for s in SIDES}
sec_changed = {s: 0 for s in SIDES}
sec_peak = {s: deque(maxlen=FPS) for s in SIDES}
hist = {s: deque(maxlen=6) for s in SIDES}  # (t, min_peak, max_peak, moved) per second
dead = {s: None for s in SIDES}
n = 0
t0 = time.monotonic()

print(f"soaking {', '.join(SIDES)} at {FPS} Hz for {DURATION:.0f}s")
print("PRESS EACH FINGER HARD a few times during this, and say roughly when.\n")
print(f"  {'t(s)':>6}  " + "  ".join(f"{s:>31}" for s in SIDES))
print(f"  {'':>6}  " + "  ".join(f"{'peak lo..hi   moved frzn link':>31}" for _ in SIDES))

last_report = 0.0
while (t := time.monotonic() - t0) < DURATION:
    tick = time.monotonic()
    reads = arr.read()
    n += 1
    for s in SIDES:
        v = reads[s].raw
        sec_peak[s].append(float(v.max()))
        if prev[s] is not None and not np.array_equal(v, prev[s]):
            changed[s] += 1
            sec_changed[s] += 1
        prev[s] = v.copy()

    if t - last_report >= 1.0:
        last_report = t
        row = f"  {t:6.1f}  "
        for s in SIDES:
            pk = sec_peak[s]
            lo, hi = (min(pk), max(pk)) if pk else (0, 0)
            frz = float(reads[s].status[4])
            # valid (status[3]) distinguishes an MCU hang from a yanked cable. The
            # reader holds its last value either way, so frozen_s climbs identically
            # for both, and printing it alone will send you after the wrong bug.
            ok = float(reads[s].status[3]) > 0.5
            hist[s].append((t, lo, hi, sec_changed[s]))
            flag = "*" if hi - lo > 300 else " "
            row += (f"{lo:6.0f}..{hi:<6.0f}{flag}{sec_changed[s]:4d} {frz:5.1f} "
                    f"{'ok' if ok else 'GONE':>4}  ")
            sec_changed[s] = 0
        print(row, flush=True)

        for s in SIDES:
            if dead[s] is None and float(reads[s].status[4]) >= 2.0:
                dead[s] = t
                if float(reads[s].status[3]) > 0.5:
                    kind = "FROZE (MCU hang, USB link still up)"
                else:
                    kind = ("LOST ITS USB LINK (valid=0). This is NOT a freeze. "
                            "Check dmesg -T for a disconnect before concluding anything")
                print(f"\n  >>> {s} {kind} at t={t:.1f}s. Load history for the 5s before:",
                      flush=True)
                for ht, lo, hi, mv in hist[s]:
                    tag = "  <- big press" if hi - lo > 300 else ""
                    print(f"        t={ht:6.1f}  peak {lo:6.0f}..{hi:<6.0f}  moved {mv:3d}/30{tag}",
                          flush=True)
                print(flush=True)

    if all(d is not None for d in dead.values()):
        print("  both fingers dead, stopping early\n", flush=True)
        break

    dt = time.monotonic() - tick
    if dt < 1 / FPS:
        time.sleep(1 / FPS - dt)

print("=" * 78)
for s in SIDES:
    r = arr.reader(s)
    print(f"  {s:13s} moved {changed[s]}/{n}   dropped {getattr(r, 'dropped', '?')}   "
          f"push_errors {getattr(r, 'push_errors', '?')}   "
          f"died at {f'{dead[s]:.1f}s' if dead[s] is not None else 'NEVER (survived)'}")
print("=" * 78)
arr.disconnect()
