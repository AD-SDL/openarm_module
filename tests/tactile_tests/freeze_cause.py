"""Did the fingers die from force, or from something else?

Correlates each finger's freeze onset against (a) how loaded that finger was at the
moment it stopped, and (b) what the grippers and arm joints were doing. Both signals
are in the same parquet at the same timestamps, so the correlation is exact rather
than reconstructed from log lines.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/.cache/huggingface/lerobot/local/tactile_smoke_20260911_011520"
)

info = json.load(open(f"{root}/meta/info.json"))
state_names = info["features"]["observation.state"]["names"]
files = sorted(glob.glob(f"{root}/data/**/*.parquet", recursive=True))
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
print(f"{len(df)} frames, {df.episode_index.nunique()} episodes, {len(files)} parquet file(s)\n")

state = np.stack(df["observation.state"].to_numpy())
action = np.stack(df["action"].to_numpy())
idx = {n: i for i, n in enumerate(state_names)}
grip = [n for n in state_names if "gripper" in n]
print("gripper channels in observation.state:", grip, "\n")


def global_t(sub):
    """Monotonic seconds across episodes; timestamp restarts each episode."""
    return sub["timestamp"].to_numpy()


for side in ("right_finger", "left_finger"):
    col = f"observation.tactile.{side}"
    a = np.stack(df[col].to_numpy())
    base = np.stack(df[f"{col}.baseline"].to_numpy())
    st = np.stack(df[f"{col}.status"].to_numpy())
    raw = a + base
    ep = df["episode_index"].to_numpy()
    t = df["timestamp"].to_numpy()

    changed = (np.diff(a, axis=0) != 0).any(axis=1)

    # valid (status[3]) separates an MCU hang from a dropped USB link. Both freeze the
    # payload, because the reader holds its last value either way, so frozen_s alone
    # cannot tell them apart and will send you after the wrong bug.
    v = st[:, 3]
    n_bad = int((v < 0.5).sum())
    link = (f"USB LINK DROPPED on {n_bad}/{len(v)} frames -- cross-check dmesg -T, "
            f"this is not necessarily a freeze" if n_bad else
            "USB link up on every frame, so any freeze here is a real MCU hang")

    print("=" * 78)
    print(f"=== {side} ===")
    print(f"  {link}")

    if not changed.any():
        print(f"  never moved at all in this dataset\n")
        continue
    onset = int(np.where(changed)[0][-1]) + 1  # first index of the constant run
    if len(a) - onset < 60:  # under 2 s of stillness is not a freeze
        print(f"  SURVIVED: moved on {int(changed.sum())}/{len(a) - 1} frames, and the "
              f"final still run is only {(len(a) - onset) / 30:.1f}s (freeze threshold 2.0s)\n")
        continue
    print(f"  baseline: min {base[0].min():.0f} max {base[0].max():.0f}   "
          f"({'TARED' if base[0].max() > 0 else 'NOT tared -- tare was rejected, so tared == raw'})")
    print(f"  frames that moved: {int(changed.sum())}/{len(a) - 1}")
    print(f"  freeze onset: row {onset}  episode {ep[onset]}  t={t[onset]:.2f}s into that episode")
    print(f"  frozen for the last {len(a) - onset} rows ({(len(a) - onset) / 30:.1f}s of recording)")

    peak = raw.max(axis=1)
    total = raw.sum(axis=1)
    print(f"\n  RAW peak taxel over the whole run:  min {peak.min():.0f}  "
          f"median {np.median(peak):.0f}  max {peak.max():.0f}")
    print(f"  RAW peak at the instant it froze:   {peak[onset]:.0f}   "
          f"({100 * (peak[onset] - peak.min()) / max(1e-9, peak.max() - peak.min()):.0f}% of the observed range)")

    # Was it being squeezed in the 3 s before death?
    lo = max(0, onset - 90)
    pre = peak[lo:onset]
    print(f"  RAW peak in the 3s before it froze: min {pre.min():.0f}  max {pre.max():.0f}  "
          f"swing {pre.max() - pre.min():.0f} counts")

    print(f"\n  {'t(s)':>7} {'ep':>3} {'tac_peak':>9} {'tac_total':>10} ", end="")
    for g in grip:
        print(f"{g.replace('gripper', 'grp'):>16}", end="")
    print()
    lo, hi = max(0, onset - 45), min(len(a), onset + 15)
    for i in range(lo, hi, 3):
        mark = "  <== FROZEN FROM HERE" if lo <= onset < lo + 3 * ((i - lo) // 3 + 1) and i >= onset > i - 3 else ""
        print(f"  {t[i]:7.2f} {ep[i]:3d} {peak[i]:9.0f} {total[i]:10.0f} ", end="")
        for g in grip:
            print(f"{state[i, idx[g]]:16.3f}", end="")
        print(mark)
    print()

# How much did the arms actually move during each episode?
print("=" * 78)
print("Arm activity per episode (was anything actually being teleoperated?)")
pos = [n for n in state_names if n.endswith(".pos")]
for e in sorted(df.episode_index.unique()):
    sub = state[df.episode_index.to_numpy() == e]
    rng = {n: np.ptp(sub[:, idx[n]]) for n in pos}  # ndarray.ptp() removed in NumPy 2.0
    movers = {k: v for k, v in sorted(rng.items(), key=lambda kv: -kv[1]) if v > 0.5}
    print(f"  episode {e}: {len(movers)} joints moved >0.5 units; "
          f"top: {', '.join(f'{k}={v:.1f}' for k, v in list(movers.items())[:6]) or 'NONE -- arms were static'}")
