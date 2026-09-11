# Tactile test scripts

Diagnostics for the two Sensible Robotics tactile fingers on the OpenArm. Every script
here opens both fingers through a single `TactileArray` and needs the lerobot venv:

```bash
source ~/humanoids/lerobot/.venv/bin/activate
```

## Recording

`record_tactile.sh` is the record wrapper. `EPISODES`, `EP_TIME`, `TASK` and `REPO` are
environment overrides.

```bash
EPISODES=6 bash record_tactile.sh
```

## Live diagnostics

These run against the hardware with no CAN and no arms.

| script | what it answers |
|---|---|
| `finger_soak.py [dur_s] [sides]` | do the fingers freeze on their own, with nothing else running |
| `press_soak.py [dur_s] [sides]` | does force trigger it, by tracing load against the moment of death |
| `rs_soak.py [baseline_s] [total_s]` | does the RealSense trigger it, by starting the camera mid-soak at a known instant |

All three refuse to start on an already-hung finger. Without that pre-flight check a
finger left frozen by a previous run reads as healthy on every other signal and
silently voids the entire soak.

## Offline analysis

These read a recorded LeRobot dataset and take its root as their one argument.

| script | what it answers |
|---|---|
| `freeze_cause.py [dataset_root]` | did anything freeze during the recording, and what was the gripper doing at the time |
| `tactile_quality.py [dataset_root]` | is the recorded tactile actually worth training on |

`tactile_quality.py` reports the number that decides whether a policy will use the
sensor at all: the correlation between tactile total force and gripper position. If
that approaches 1.0 the policy can predict tactile from proprioception and will learn
to ignore the fingers. Measured at +0.32 on `tactile_smoke_20260911_021920`, which is
healthy.

## Two things to know before reading any output

**A frozen sensor looks perfectly healthy on every signal except `frozen_s`.** The ADC
scan stops while the MIDI transmit path keeps running, so `seq` keeps advancing,
`dropped` stays 0 and `age_s` stays in milliseconds, all while the 80-taxel payload
repeats bit for bit. Only `frozen_s` catches it, with a threshold of 2.0 s.

**A yanked cable is indistinguishable from a freeze if you look only at `frozen_s`.**
The reader holds its last value in both cases, so `frozen_s` climbs identically for an
MCU hang and for a disconnect. `valid`, which is `status[3]`, is what separates them,
and every script here now prints it as an `ok` or `GONE` column. When one reads `GONE`,
go and check `dmesg -T` for a disconnect before blaming the device. Getting this
backwards once cost an hour of chasing a hub fault that was really a manual hub reset.

## What was actually causing the freezes

Both USB splitters were passive, with no external power. On a passive hub everything
draws through one upstream port budgeted at 900 mA, and the VIA hub was carrying
100 + 100 + 720 mA against that while the Genesys hub carried 1240 mA. The fingers were
the most fragile load on the rail.

Powering both hubs fixed it. Confirmed over a six-episode record run with three cameras,
both CAN buses and lossless depth encoding all active: 3593 of 3593 frames moved on each
finger, `dropped` 0, `valid` on every frame, and a maximum `frozen_s` of 0.02 s against
the 2.0 s threshold.

If it ever comes back, move the fingers to the Thunderbolt controller on buses 3 and 4,
which is separate silicon from the PCH controller both hubs hang off and is completely
empty. That needs two USB-C to USB-A adapters and a `sensible-finger bind` to rewrite
the topology field in `~/.config/sensible_finger/bindings.toml`.
