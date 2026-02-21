# OpenArm + LeRobot Integration

Complete integration of OpenArm bimanual robots with HuggingFace LeRobot for robotic learning and teleoperation.

This repository contains a modified fork of LeRobot with OpenArm-specific enhancements for bimanual manipulation, gamepad teleoperation, and hardware calibration synchronization.

## Features

- **Bimanual OpenArm Support**: Control two OpenArm follower robots simultaneously
- **Gamepad Teleoperation**: PlayStation/Xbox controller support for intuitive joint control
- **Hardware Calibration Sync**: Proper integration with OpenArm's hardware calibration system
- **Velocity & Torque Support**: Full action space including position, velocity, and torque
- **Recording & Replay**: Compatible with LeRobot's dataset recording and policy training


## 🛠️ Installation

### Prerequisites

- Ubuntu 22.04 or 24.04
- Python 3.10+
- Two OpenArm follower robots with CAN bus connectivity
- PlayStation DualSense or Xbox controller
- Root access for CAN bus configuration

### Step 1: Install LeRobot Fork

This module requires the AD-SDL LeRobot fork with OpenArm support:

```bash
# In your project directory clone the LeRobot fork
git clone https://github.com/AD-SDL/lerobot.git
cd lerobot

# Install with PDM (recommended - uses lock file)
pdm install

# OR install with pip
pip install -e .

cd ..
```

### Step 2: Install System Dependencies

```bash
# Clone this repository
git clone https://github.com/AD-SDL/openarm_module.git
cd openarm_module

# Run system setup (installs OpenArm packages and configures auto CAN setup)
bash setup_system.sh
```

This script will:
- Install OpenArm system packages (`openarm-can-utils`, CLI tools)
- Configure udev rules for automatic CAN configuration on USB connection
- Set up CAN interfaces for current session

### Step 3: Install Python Dependencies

```bash
# Install with PDM
pdm install

# OR install with pip
pip install -e .
```

## Hardware Calibration

### Check Current Calibration

**IMPORTANT**: The robots are already calibrated at the factory. Only recalibrate if you suspect the zero positions are incorrect (e.g., arms don't return to proper zero position).

**To verify calibration:**
```bash
# Move arms to zero to check if calibration is correct
python scripts/move_to_zero.py
```

If the arms move to a centered, symmetric position (hanging down naturally), calibration is good. **Skip to Sync Calibration below.**

If the arms move to awkward or asymmetric positions, proceed with recalibration.

### Recalibrate Hardware (Only if needed)

**WARNING**: This will overwrite the existing calibration. Only do this if verification above failed.

```bash
# Calibrate right arm (can0)
openarm-can-zero-position-calibration --canport can0 --arm-side right_arm

# Calibrate left arm (can1)
openarm-can-zero-position-calibration --canport can1 --arm-side left_arm
```

This tool:
1. Moves each joint to its mechanical stops
2. Calculates the center position
3. Sets that as zero in motor memory
4. Stores the calibration permanently

### Sync Calibration with LeRobot

**REQUIRED**: After verifying or recalibrating hardware, sync LeRobot's calibration files with the hardware zero positions:

```bash
# Delete old LeRobot calibration files (if any)
rm -rf ~/.cache/huggingface/lerobot/calibration/robots/bi_openarm_follower/

# Run calibration sync script
# This moves arms to hardware zero and creates LeRobot calibration files
python scripts/sync_calibration.py
```

**What this does:**
1. Uses OpenArm C++ library to move arms to hardware-calibrated zero
2. Connects LeRobot and sets current position as LeRobot's zero
3. Saves calibration files to `~/.cache/huggingface/lerobot/calibration/`


### Verify CAN Interfaces

After plugging in USB-CAN adapters, verify they're configured:

```bash
# Check CAN interfaces
ip link show can0 can1

# Should show both as UP and RUNNING
# If not, unplug and replug USB-CAN adapters (auto-configures via udev)
```

### Manual CAN Configuration (if needed)

If auto-configuration doesn't work:

```bash
openarm-can-configure-socketcan can0 -fd -b 1000000 -d 5000000
openarm-can-configure-socketcan can1 -fd -b 1000000 -d 5000000
```

## Quick Start

After installation and calibration:

```bash
# Test teleoperation
lerobot-teleoperate \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --teleop.type=openarm_bi_gamepad_joints \
    --teleop.joint_velocity_scale=60.0
```

Use the gamepad to control the robots. Press Square/X to toggle between left/right arm!

## 🎮 Teleoperation

### Start Gamepad Teleoperation

```bash
lerobot-teleoperate \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --teleop.type=openarm_bi_gamepad_joints \
    --teleop.joint_velocity_scale=60.0
```

### Gamepad Controls

**Important:** Use `--teleop.type=openarm_bi_gamepad_joints` for bimanual control (two arms), or `--teleop.type=openarm_gamepad_joints` for single arm control.

- **Left Stick**: Control joint 1-2
- **Right Stick**: Control joint 3-4
- **D-Pad**: Control joint 5-7
- **L1/R1**: Open/close gripper
- **PS/Xbox Button**: Return active arm to zero position
- **Square/X**: Toggle between left/right arm (bimanual mode)
- **Triangle/Y**: Print current arm position
- **Circle/B**: Exit teleoperation

### Common Issues

**Controller not responding:**
- Disconnect and reconnect the controller
- Check controller is detected: `ls /dev/input/js*`
- Restart the teleoperation script

**Arms move too fast/slow:**
- Adjust `--teleop.joint_velocity_scale` (default: 60.0)
- Lower values = slower movement
- Higher values = faster movement

## Recording Demonstrations

```bash
export HF_HUB_OFFLINE=1

lerobot-record \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --teleop.type=openarm_bi_gamepad_joints \
    --teleop.joint_velocity_scale=60.0 \
    --dataset.repo_id=local/my_task \
    --dataset.single_task="Task description" \
    --dataset.fps=60 \
    --dataset.num_episodes=50 \
    --dataset.episode_time_s=30 \
    --dataset.reset_time_s=10 \
    --dataset.push_to_hub=false
```

**Recording Parameters:**
- `--dataset.fps`: Recording framerate (60 fps recommended for smooth playback)
- `--dataset.num_episodes`: Number of demonstrations
- `--dataset.episode_time_s`: Maximum episode duration
- `--dataset.reset_time_s`: Time to reset between episodes

**Dataset location:** `~/.cache/huggingface/lerobot/local/`

## Replay Demonstrations

```bash
lerobot-replay \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --dataset.fps=60 \
    --dataset.repo_id=local/my_task \
    --dataset.episode=0
```

## Training Policies

Train an ACT policy on recorded demonstrations:

```bash
python lerobot/scripts/train.py \
    policy=act \
    env=bi_openarm_follower \
    dataset_repo_id=local/my_task \
    training.offline_steps=100000 \
    training.batch_size=8 \
    training.eval_freq=10000
```

## Key Modifications in LeRobot Fork

This module depends on the `lerobot` fork which contains the following modifications from upstream LeRobot:

### 1. OpenArm Follower Robot (`lerobot/src/lerobot/robots/openarm_follower/`)

**openarm_follower.py:**
- Removed `set_zero_position()` call from `connect()` to preserve hardware calibration
- Added full action space support (position, velocity, torque)
- Optimized `get_observation()` to read all motor states in one CAN refresh cycle

**config_openarm_follower.py:**
- Configured motor IDs and types for 7-DOF + gripper
- Set appropriate kp/kd gains per joint
- Defined joint limits for left/right arm configurations

### 2. Bimanual OpenArm (`src/lerobot/robots/bi_openarm_follower/`)

- Created bimanual robot wrapper for dual OpenArm control
- Synchronized action/observation spaces across both arms
- Added proper torque enable/disable on connect/disconnect

### 3. Gamepad Teleoperation (`src/lerobot/teleoperators/openarm_gamepad/`)

**openarm_teleop_gamepad.py:**
- Direct joint control mode for OpenArm
- PlayStation controller button mapping
- Return-to-zero functionality

**openarm_bi_teleop_gamepad.py:**
- Bimanual control with arm toggle
- Independent left/right arm control
- Synchronized gripper control

**gamepad_utils.py modifications:**
- Added `get_button()` method to `GamepadController`
- Enhanced button state tracking
- Improved analog stick dead zone handling

### 4. Recording System (`src/lerobot/teleoperators/gamepad/`)

**teleop_bi_gamepad_joints.py:**
- Added velocity and torque fields to action dictionary
- Fixed action registration for bimanual recording
- Proper integration with LeRobot's dataset format

## Repository Structure

```
openarm_module/
├── README.md
├── pyproject.toml                 # Python package configuration
├── scripts/
│   ├── setup_system.sh            # System setup (OpenArm packages + CAN)
│   ├── sync_calibration.py        # Sync hardware calibration with LeRobot
│   └── move_to_zero.py           # Utility to move arms to zero
├── src/
│   └── openarm_module/            # Main module code
│       ├── __init__.py
│       └── ...                    # TODO
└── tests/
```

**Note**: This module depends on the `lerobot` fork, which should be installed separately (see Installation).

## Troubleshooting

### CAN Bus Issues

```bash
# Check CAN interfaces are up
ip link show can0
ip link show can1

# Restart CAN interfaces
sudo ip link set down can0
sudo ip link set down can1
sudo ip link set can0 type can bitrate 1000000 dbitrate 5000000 fd on
sudo ip link set up can0
sudo ip link set can1 type can bitrate 1000000 dbitrate 5000000 fd on
sudo ip link set up can1

# Check for CAN errors
candump can0
candump can1
```

### Motor Communication Errors

```bash
# Test motor communication
openarm-can-motor-check --canport can0
openarm-can-motor-check --canport can1

# Check motor IDs match configuration
openarm-can-diagnosis --canport can0
```

### Calibration Issues

If arms don't return to correct zero position:

1. **Re-run hardware calibration:**
   ```bash
   openarm-can-zero-position-calibration --canport can0 --arm-side right_arm
   openarm-can-zero-position-calibration --canport can1 --arm-side left_arm
   ```

2. **Delete LeRobot calibration and re-sync:**
   ```bash
   rm -rf ~/.cache/huggingface/lerobot/calibration/
   python scripts/sync_calibration.py
   ```

3. **Verify zero position:**
   ```bash
   python scripts/move_to_zero.py
   ```

### Dataset Recording Issues

**Dataset not saving:**
- Check disk space: `df -h`
- Verify HF_HUB_OFFLINE is set: `echo $HF_HUB_OFFLINE`
- Check dataset path exists: `ls ~/.cache/huggingface/lerobot/`

**Missing velocity/torque in observations:**
- This was a bug in earlier versions
- Update to latest version from this repository
- Observations should include `.pos`, `.vel`, and `.torque` for all joints

## Documentation

- [LeRobot Documentation](https://huggingface.co/docs/lerobot)
- [OpenArm CAN Documentation](https://docs.openarm.dev/software/can)

## Contributing

Contributions are welcome! Please:

1. Fork this repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with a clear description

## License

This project inherits the Apache 2.0 license from HuggingFace LeRobot.

## Acknowledgments

- **HuggingFace LeRobot Team** for the excellent robotic learning framework
- **Enactic/OpenArm** for the robot hardware and CAN library
- **AD-SDL/Argonne National Laboratory** for supporting this integration

## Contact

For questions and support:
- Open an issue in this repository: [AD-SDL/openarm_module](https://github.com/AD-SDL/openarm_module/issues)
- Contact: Rapid Prototyping Laboratory, Argonne National Laboratory

## Related Projects

- [lerobot-rpl](https://github.com/AD-SDL/lerobot) - LeRobot fork with OpenArm support
- [LeRobot](https://github.com/huggingface/lerobot) - Original LeRobot framework
- [OpenArm CAN](https://github.com/enactic/openarm_can) - OpenArm CAN library

---

**Note**: This is a research project. Use at your own risk and always ensure safety when operating robotic systems.