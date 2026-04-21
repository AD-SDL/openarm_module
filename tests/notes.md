# TEST
lerobot-record \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.left_arm_config.cameras="{ \
        chest: {type: intelrealsense, serial_number_or_name: 025222071898, width: 848, height: 480, fps: 30, use_depth: true}, \
        wrist_left: {type: opencv, index_or_path: /dev/video-wrist-left, width: 640, height: 480, fps: 30, fourcc: MJPG} \
    }" \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --robot.right_arm_config.cameras="{ \
        wrist_right: {type: opencv, index_or_path: /dev/video-wrist-right, width: 640, height: 480, fps: 30, fourcc: MJPG} \
    }" \
    --robot.id=my_bimanual_follower \
    --teleop.type=bi_openarm_leader \
    --teleop.left_arm_config.port=can3 \
    --teleop.right_arm_config.port=can2 \
    --teleop.id=my_bimanual_leader \
    --teleop.left_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
    --teleop.left_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
    --teleop.right_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
    --teleop.right_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
    --dataset.repo_id=local/test \
    --dataset.single_task="Test recording" \
    --dataset.fps=30 \
    --dataset.num_episodes=5 \
    --dataset.episode_time_s=40 \
    --dataset.reset_time_s=10 \
    --dataset.push_to_hub=false \
    --display_data=true


# RECORD


lerobot-record \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.left_arm_config.cameras="{ \
        chest: {type: intelrealsense, serial_number_or_name: 025222071898, width: 848, height: 480, fps: 30, use_depth: true}, \
        wrist_left: {type: opencv, index_or_path: /dev/video-wrist-left, width: 640, height: 480, fps: 30, fourcc: MJPG} \
    }" \
    --robot.right_arm_config.port=can0 \
    --robot.right_arm_config.side=right \
    --robot.right_arm_config.cameras="{ \
        wrist_right: {type: opencv, index_or_path: /dev/video-wrist-right, width: 640, height: 480, fps: 30, fourcc: MJPG} \
    }" \
    --robot.id=my_bimanual_follower \
    --teleop.type=bi_openarm_leader \
    --teleop.left_arm_config.port=can3 \
    --teleop.right_arm_config.port=can2 \
    --teleop.id=my_bimanual_leader \
    --teleop.left_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
    --teleop.left_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
    --teleop.right_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
    --teleop.right_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
    --dataset.repo_id=local/openarm_open_lab_door \
    --dataset.single_task="Open lab door handle" \
    --dataset.fps=30 \
    --dataset.num_episodes=10 \
    --dataset.episode_time_s=40 \
    --dataset.reset_time_s=10 \
    --dataset.push_to_hub=false \
    --resume=true \
    --display_data=true