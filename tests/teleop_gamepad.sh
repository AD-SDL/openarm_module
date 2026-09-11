#!/usr/bin/env bash
# Bare gamepad teleop. No cameras, no tactile, no recording.
# First step: prove the arms move under the pad before adding anything else.
set -u

source "$HOME/humanoids/lerobot/.venv/bin/activate"

lerobot-teleoperate \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --teleop.type=openarm_bi_gamepad_joints \
    --teleop.joint_velocity_scale=60.0
