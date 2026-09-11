"""Is this dataset actually trainable on tactile, or six minutes of untouched sensor?

Freeze detection only proves the sensor was alive. A policy needs contact events that
correlate with what the gripper was doing, and it needs them to vary across episodes.
This measures that directly rather than assuming it.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/.cache/huggingface/lerobot/local/tactile_smoke_20260911_021920"
)

info = json.load(open(f"{root}/meta/info.json"))
state_names = info["features"]["observation.state"]["names"]
idx = {n: i for i, n in enumerate(state_names)}
files = sorted(glob.glob(f"{root}/data/**/*.parquet", recursive=True))
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
state = np.stack(df["observation.state"].to_numpy())
ep = df["episode_index"].to_numpy()

# Contact threshold: 5x the measured no-load per-taxel sigma of ~0.92 counts, so a
# taxel is "in contact" only well clear of dither.
THRESH = 30.0

print(f"{len(df)} frames, {df.episode_index.nunique()} episodes\n")

for side in ("right_finger", "left_finger"):
    col = f"observation.tactile.{side}"
    a = np.stack(df[col].to_numpy())
    st = np.stack(df[f"{col}.status"].to_numpy())
    der = np.stack(df[f"{col}.derived"].to_numpy())
    peak = a.max(axis=1)
    n_contact_taxels = (a > THRESH).sum(axis=1)

    print("=" * 78)
    print(f"=== {side} ===")
    print(f"  status over the whole run: dropped total {st[:, 2].sum():.0f}, "
          f"valid on {int((st[:, 3] > 0.5).sum())}/{len(st)}, "
          f"max frozen_s {st[:, 4].max():.2f}")
    print(f"  age_s: median {np.median(st[:, 1]) * 1000:.1f} ms, max {st[:, 1].max() * 1000:.1f} ms")
    print(f"  tared peak: median {np.median(peak):.0f}  p95 {np.percentile(peak, 95):.0f}  "
          f"max {peak.max():.0f}")
    print(f"  frames with any taxel over {THRESH:.0f}: {int((n_contact_taxels > 0).sum())}"
          f"/{len(a)} ({100 * (n_contact_taxels > 0).mean():.0f}%)")
    print()
    print(f"  {'ep':>3} {'peak max':>9} {'contact frames':>15} {'max taxels lit':>15} "
          f"{'grip range':>11}")
    for e in sorted(df.episode_index.unique()):
        m = ep == e
        gr = np.ptp(state[m, idx["right_gripper.pos"]])
        print(f"  {e:3d} {peak[m].max():9.0f} {int((n_contact_taxels[m] > 0).sum()):9d}/{m.sum():<5d} "
              f"{n_contact_taxels[m].max():15d} {gr:11.1f}")
    print()

# Does tactile carry information the gripper position does not already carry? If the
# correlation is near 1 the policy can predict tactile from proprioception and will
# ignore the sensor. This is the causal-confusion check, not a data-quality check.
print("=" * 78)
print("Is tactile redundant with gripper position? (the copycat check)")
for side in ("right_finger", "left_finger"):
    a = np.stack(df[f"observation.tactile.{side}"].to_numpy())
    tot = a.sum(axis=1)
    for g in ("right_gripper.pos", "left_gripper.pos"):
        gp = state[:, idx[g]]
        if np.ptp(gp) < 1e-6 or np.ptp(tot) < 1e-6:
            print(f"  {side} vs {g}: one signal is constant, no correlation defined")
            continue
        r = np.corrcoef(tot, gp)[0, 1]
        print(f"  {side} total force vs {g}: r = {r:+.3f}")
