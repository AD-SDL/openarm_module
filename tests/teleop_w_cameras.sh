

# python3 -c "import pyrealsense2 as rs; ctx = rs.context(); print([d.get_info(rs.camera_info.serial_number) for d in ctx.devices])"
source ~/humanoids/lerobot_env/bin/activate

v4l2-ctl --device=/dev/video-wrist-left --set-fmt-video=width=640,height=480,pixelformat=MJPG
v4l2-ctl --device=/dev/video8 --set-fmt-video=width=640,height=480,pixelformat=MJPG

lerobot-teleoperate \
    --robot.type=bi_openarm_follower \
    --robot.left_arm_config.port=can1 \
    --robot.left_arm_config.side=left \
    --robot.left_arm_config.cameras="{ \
        chest: {type: intelrealsense, serial_number_or_name: 025222071898, width: 848, height: 480, fps: 30}, \
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
    --teleop.left_arm_config.manual_control=true \
    --teleop.right_arm_config.manual_control=true \
    --teleop.id=my_bimanual_leader \
    --teleop.left_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
    --teleop.left_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
    --teleop.right_arm_config.position_kp="[60,60,30,10,6,7,6,1]" \
    --teleop.right_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
    --robot.left_arm_config.position_kp="[240,240,120,40,24,31,25,5]" \
    --robot.left_arm_config.position_kd="[5,5,1.5,0.3,0.3,0.3,0.3,0.05]" \
    --robot.right_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
    --robot.right_arm_config.position_kd="[5,5,1.5,0.3,0.3,0.3,0.3,0.05]" \
    --display_data=true \
    --display_mode="foxglove"

# lerobot-teleoperate \
#     --robot.type=bi_openarm_follower \
#     --robot.left_arm_config.port=can1 \
#     --robot.left_arm_config.side=left \
#     --robot.left_arm_config.cameras="{ \
#         chest: {type: intelrealsense, serial_number_or_name: 025222071898, width: 848, height: 480, fps: 30}, \
#         wrist_left: {type: opencv, index_or_path: /dev/video-wrist-left, width: 640, height: 480, fps: 30, fourcc: MJPG} \
#     }" \
#     --robot.right_arm_config.port=can0 \
#     --robot.right_arm_config.side=right \
#     --robot.right_arm_config.cameras="{ \
#         wrist_right: {type: opencv, index_or_path: /dev/video-wrist-right, width: 640, height: 480, fps: 30, fourcc: MJPG} \
#     }" \
#     --robot.id=my_bimanual_follower \
#     --teleop.type=bi_openarm_leader \
#     --teleop.left_arm_config.port=can3 \
#     --teleop.right_arm_config.port=can2 \
#     --teleop.id=my_bimanual_leader \
#     --teleop.left_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
#     --teleop.left_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
#     --teleop.right_arm_config.position_kp="[120,120,60,20,12,15,12,2]" \
#     --teleop.right_arm_config.position_kd="[2,2,1.0,0.5,0.1,0.1,0.1,0.02]" \
#     --robot.left_arm_config.position_kp="[240,240,120,40,24,31,25,5]" \
#     --robot.left_arm_config.position_kd="[5,5,1.5,0.3,0.3,0.3,0.3,0.05]" \
#     --robot.right_arm_config.position_kp="[240,240,120,40,24,31,25,5]" \
#     --robot.right_arm_config.position_kd="[5,5,1.5,0.3,0.3,0.3,0.3,0.05]" \
#     --display_data=true
