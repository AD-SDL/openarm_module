#!/usr/bin/env bash
# Record with tactile. Gamepad teleop, both fingers on the right gripper.
#
# Differences from the old record_w_cameras.sh, all of them load-bearing:
#   * venv is lerobot/.venv; ~/humanoids/lerobot_env no longer exists
#   * RealSense serial is 327122076093; the old 025222071898 is not this camera
#   * leader arms need can2/can3, which this box does not have, so gamepad
#   * use_velocity_and_torque=true, without which the schema is 16 wide, not 48,
#     and cannot be pooled with the existing 102-episode dataset
#   * no --robot.id: calibration is saved under the default bi_openarm_follower_*,
#     and any other id sends connect() into the full limit-finding routine
set -u

export HF_HUB_OFFLINE=1
source "$HOME/humanoids/lerobot/.venv/bin/activate"

TASK="${TASK:-grasp and lift}"
REPO="${REPO:-local/tactile_smoke}"
EPISODES="${EPISODES:-2}"
EP_TIME="${EP_TIME:-20}"

# The wrist cameras negotiate YUYV at 640x480 unless told otherwise, which caps
# them well under 30 fps. Set the format before lerobot opens them.
v4l2-ctl --device=/dev/video-wrist-left  --set-fmt-video=width=640,height=480,pixelformat=MJPG
v4l2-ctl --device=/dev/video-wrist-right --set-fmt-video=width=640,height=480,pixelformat=MJPG

lerobot-record \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.left_arm_config.use_velocity_and_torque=true \
    --robot.left_arm_config.cameras="{ \
        chest: {type: intelrealsense, serial_number_or_name: 327122076093, width: 848, height: 480, fps: 30, use_depth: true}, \
        wrist_left: {type: opencv, index_or_path: /dev/video-wrist-left, width: 640, height: 480, fps: 30, fourcc: MJPG} \
    }" \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --robot.right_arm_config.use_velocity_and_torque=true \
    --robot.right_arm_config.tactile.sides="[right_finger, left_finger]" \
    --robot.right_arm_config.cameras="{ \
        wrist_right: {type: opencv, index_or_path: /dev/video-wrist-right, width: 640, height: 480, fps: 30, fourcc: MJPG} \
    }" \
    --teleop.type=openarm_bi_gamepad_joints \
    --teleop.joint_velocity_scale=60.0 \
    --dataset.repo_id="$REPO" \
    --dataset.single_task="$TASK" \
    --dataset.fps=30 \
    --dataset.num_episodes="$EPISODES" \
    --dataset.episode_time_s="$EP_TIME" \
    --dataset.reset_time_s=10 \
    --dataset.push_to_hub=false \
    --display_data=false
