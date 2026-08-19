#!/usr/bin/env python3
"""
OpenArm Robot Interface
=======================
Clean interface layer for the OpenArm bimanual robot over CAN bus.
Wraps the openarm_can Python bindings with higher-level methods.

Supported methods:
    home(speed)          - Move all joints to zero position
    moveJ(angles, speed) - Move to joint configuration (radians)
    getJ()               - Get current joint positions (radians)
    moveL(pose, speed)   - [STUB] Move end-effector to Cartesian pose (requires IK)
    getL()               - [STUB] Get end-effector Cartesian pose (requires FK)

Speed parameter (0.0–1.0):
    Motion duration is interpolated between MAX_MOVE_DURATION (slow, speed=0)
    and MIN_MOVE_DURATION (fast, speed=1). All moves use cosine easing so the
aaa    arm accelerates and decelerates smoothly rather than jumping to target.
"""

import time
import numpy as np
from lerobot.robots.bi_openarm_follower import BiOpenArmFollower, BiOpenArmFollowerConfig
from lerobot.robots.openarm_follower import OpenArmFollowerConfig, OpenArmFollower
from lerobot.scripts.lerobot_replay import replay, ReplayConfig, DatasetReplayConfig
from pathlib import Path

# ---------------------------------------------------------------------------
# Motor configuration constants (matches LeRobot OpenArm setup)
# ---------------------------------------------------------------------------


NUM_ARM_JOINTS = 7

# MIT gains — static, tuned for smooth movement. Do not use as a speed knob.
# To adjust stiffness/compliance change these, not the speed parameter.
DEFAULT_KP = [60.0, 60.0, 60.0, 60.0, 6.0, 8.0, 6.0, 6.0]  # index 7 = gripper
DEFAULT_KD = [2.0,  2.0,  1.5,  2.0,  0.2, 0.2, 0.2, 0.2]

# Control loop
CONTROL_RATE_HZ = 60
CONTROL_DT = 1.0 / CONTROL_RATE_HZ

# Motion duration bounds (seconds). Speed parameter maps linearly between these.
MIN_MOVE_DURATION = 2.0   # speed = 1.0 (fast)
MAX_MOVE_DURATION = 10.0  # speed = 0.0 (slow)
DEFAULT_SPEED = 0.3       # conservative default


# ---------------------------------------------------------------------------
# IK / FK not yet implemented
# ---------------------------------------------------------------------------

class IKNotImplementedError(NotImplementedError):
    """Raised when Cartesian-space methods are called before IK is available."""


# ---------------------------------------------------------------------------
# Motion helpers
# ---------------------------------------------------------------------------

def _speed_to_duration(speed: float) -> float:
    """Convert a speed value [0.0, 1.0] to a motion duration in seconds."""
    speed = float(np.clip(speed, 0.0, 1.0))
    return MAX_MOVE_DURATION + speed * (MIN_MOVE_DURATION - MAX_MOVE_DURATION)


def _cosine_interpolate(start: np.ndarray, end: np.ndarray, time_steps: list[float]) -> np.ndarray:
    """
    Cosine-eased interpolation between start and end.
    progress in [0.0, 1.0]. Matches the zero-return profile in the teleop code.
    """
    steps = []
    for progress in time_steps:
        t = 0.5 - 0.5 * np.cos(progress * np.pi)
        steps.append(start + t * (end - start))
    return steps


# ---------------------------------------------------------------------------
# Single arm wrapper
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bimanual interface (convenience wrapper around two OpenArmSingle instances)
# ---------------------------------------------------------------------------

class OpenArmBimanual:
    """
    Convenience wrapper for simultaneous control of both arms.
    Exposes the same interface as OpenArmSingle but operates on one or both arms.
    """

    def __init__(
        self,
        right_can: str = "can0",
        left_can: str = "can1",
        kp: list[float] | None = DEFAULT_KP,
        kd: list[float] | None = DEFAULT_KD,
    ):
       left_config = OpenArmFollowerConfig(port=left_can, position_kp=kp, position_kd=kd)
       right_config = OpenArmFollowerConfig(port=right_can, position_kp=kp, position_kd=kd)
       self.bimanual_config = BiOpenArmFollowerConfig(right_arm_config=right_config, left_arm_config=left_config)
       self.arms = BiOpenArmFollower(self.bimanual_config)
    def initialize(self):
        """Initialize both arms."""
        self.arms.right_arm.connect()
        self.arms.left_arm.connect()

    def shutdown(self, right: bool = True, left: bool = True):
        """Disable one or both arms."""
        if right and self.arms.right_arm._initialized:
            self.arms.right_arm.disconnect()
        if left and self.arms.left_arm._initialized:
            self.arms.left_arm.disconnect()
    def get_left_position(self):
        left_observation = self.arms.left_arm.get_observation()
        left_pos = []
        for motor in self.arms.left_arm.bus.motors.keys():
            left_pos.append(left_observation[f"{motor}.pos"])
        return left_pos
    def get_right_position(self):
            right_observation = self.arms.right_arm.get_observation()
            right_pos = []
            for motor in self.arms.left_arm.bus.motors.keys():
                right_pos.append(right_observation[f"{motor}.pos"])
            return right_pos
    def get_both_positions(self):
        return{"left_postion": self.get_left_position, "right_position": self.get_right_position}
    
    def send_command(arm: OpenArmFollower, position: list[float]):
        robot_command = {}
        for index, motor in enumerate(arm.bus.motors.keys()):
            robot_command[f"{motor}.pos"] = position[index]
        return arm.send_action(position)
            
    def move_arms_to_target(self, right_list: list[float] | None = None, left_list: list[float] | None = None, speed: float = DEFAULT_SPEED):
        """
        Move one or both arms to zero using cosine easing.
        Reads current positions first so the arms never jump.
        Blocking — returns when complete.

        Args:
            right: Home the right arm. Defaults to True.
            left:  Home the left arm. Defaults to True.
            speed: Motion speed in [0.0, 1.0]. Defaults to DEFAULT_SPEED.
        """
        if not right_list and not left_list:
            raise ValueError("At least one arm must be selected.")
        positions = self.get_both_positions()
        arms = []
        starts = []
        paths = []
        if left_list:
            arms.append(self.arms.left_arm)
            paths.append(_cosine_interpolate(self.get_left_position(), left_list))
       
        if right_list:
            arms.append(self.arms.right_arm)
            paths.append(_cosine_interpolate(self.get_left_position(), right_list))
                   
        duration = _speed_to_duration(speed)
        steps = max(1, int(duration * CONTROL_RATE_HZ))

        # Read starting positions (getJ sets STATE callback internally)
        

        for step in range(steps):
            for index, arm in enumerate(arms):
                self.send_command(arm, paths[index][step])
            time.sleep(CONTROL_DT)

    def home(self, left: bool = True, right: bool = True, speed: float=DEFAULT_SPEED):
        left_target = None
        right_target = None
        if left:
            left_target = np.zeros(NUM_ARM_JOINTS + 1)
        if right:
            right_target = np.zeros(NUM_ARM_JOINTS + 1)
        self.move_arms_to_target(right_target, left_target, speed)
        

    def get_joint_angles(self, right: bool = True, left: bool = True) -> dict:
        """
        Read current joint state from one or both arms.

        Args:
            right: Include right arm state. Defaults to True.
            left:  Include left arm state. Defaults to True.

        Returns:
            dict with keys "right" and/or "left", each containing the same
            structure as OpenArmSingle.getJ().
        """
        result = {}
        if right:
            result["right"] = self.get_right_position()
        if left:
            result["left"] = self.get_left_position()
        return result
    def get_observation(self):
        return self.arms.get_observation()

    def replay_example(self, repo_id: str, episode: int, repo_path: Path, fps: int = 30):
        dataset_config = DatasetReplayConfig(repo_id = repo_id, episode=episode, root=repo_path, fps=fps)
        replay_config = ReplayConfig(robot = self.bimanual_config, dataset=dataset_config)
        replay(replay_config)

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    robot = OpenArmBimanual(right_can="can0", left_can="can1")

    try:
        print("Initializing arms...")
        robot.initialize()

        # Home both arms at default speed
        print("Homing both arms...")
        robot.home()

        # Home only the right arm, faster
        print("Homing right arm only at speed 0.7...")
        robot.home(right=True, left=False, speed=0.7)

        # Read state from both arms
        state = robot.getJ()
        print("Right arm positions:", state["right"]["positions"])
        print("Left arm positions: ", state["left"]["positions"])

        # Move only the right arm
        right_target = [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        print("Moving right arm only...")
        robot.moveJ(right_angles=right_target, speed=0.5)

        # Move both arms simultaneously
        left_target = [0.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0]
        print("Moving both arms...")
        robot.moveJ(right_angles=right_target, left_angles=left_target, speed=0.3)

        # Home both arms to finish
        print("Homing both arms...")
        robot.home(speed=0.5)

    finally:
        print("Shutting down...")
        robot.shutdown()
