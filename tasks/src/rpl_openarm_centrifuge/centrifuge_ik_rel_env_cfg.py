# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Bimanual OpenArm + relative differential-IK teleop variant.

Wires:
  * Robot: ``OPENARM_BI_HIGH_PD_CFG`` (stiffer PD for IK tracking).
  * Two relative-IK action terms (one per arm) on ``openarm_{left,right}_hand``.
  * Two binary gripper action terms on ``openarm_{left,right}_finger_joint.*``.
  * Bimanual hand-tracking teleop via OpenXR (one Se3Rel + Gripper retargeter per hand).
  * ``keyboard`` device wrapped so the keyboard drives the **right arm only**;
    left arm holds its default joint pose. Smoke-test path before hand-tracking.
"""

from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.devices.device_base import DeviceBase, DevicesCfg
from isaaclab.devices.openxr import XrCfg
from isaaclab.devices.openxr.openxr_device import OpenXRDeviceCfg
from isaaclab.devices.openxr.retargeters.manipulator.gripper_retargeter import GripperRetargeterCfg
from isaaclab.devices.openxr.retargeters.manipulator.se3_rel_retargeter import Se3RelRetargeterCfg
from isaaclab.envs.mdp.actions.actions_cfg import (
    BinaryJointPositionActionCfg,
    DifferentialInverseKinematicsActionCfg,
)
from isaaclab.sensors import FrameTransformerCfg
from isaaclab.sensors.frame_transformer.frame_transformer_cfg import OffsetCfg
from isaaclab.utils import configclass

from isaaclab_assets.robots.openarm import OPENARM_BI_HIGH_PD_CFG

from .centrifuge_env_cfg import CentrifugeEnvCfg
from .devices import BimanualKeyboardRightArmCfg


@configclass
class CentrifugeBimanualIkRelEnvCfg(CentrifugeEnvCfg):
    """Bimanual OpenArm with relative differential-IK actions for hand-tracking teleop."""

    xr: XrCfg = XrCfg(
        # Anchor places the user roughly in front of the table at chest height, facing the robot.
        anchor_pos=(1.4, 0.0, 1.1),
        anchor_rot=(0.0, 0.0, 0.0, 1.0),
    )

    def __post_init__(self):
        super().__post_init__()

        # robot — mount the bimanual OpenArm on top of the pedestal (matches aiet_scene.usd)
        self.scene.robot = OPENARM_BI_HIGH_PD_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.scene.robot.init_state.pos = (-0.62, 0.0, 0.5786)

        # end-effector frame transformers (relative to robot body root)
        self.scene.left_ee_frame = FrameTransformerCfg(
            prim_path="{ENV_REGEX_NS}/Robot/openarm_body_link",
            debug_vis=False,
            target_frames=[
                FrameTransformerCfg.FrameCfg(
                    prim_path="{ENV_REGEX_NS}/Robot/openarm_left_hand",
                    name="left_end_effector",
                    offset=OffsetCfg(pos=(0.0, 0.0, 0.0)),
                ),
            ],
        )
        self.scene.right_ee_frame = FrameTransformerCfg(
            prim_path="{ENV_REGEX_NS}/Robot/openarm_body_link",
            debug_vis=False,
            target_frames=[
                FrameTransformerCfg.FrameCfg(
                    prim_path="{ENV_REGEX_NS}/Robot/openarm_right_hand",
                    name="right_end_effector",
                    offset=OffsetCfg(pos=(0.0, 0.0, 0.0)),
                ),
            ],
        )

        # IK action terms — one per arm. Relative mode: action = 6-D delta pose.
        self.actions.left_arm_action = DifferentialInverseKinematicsActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_joint[1-7]"],
            body_name="openarm_left_hand",
            controller=DifferentialIKControllerCfg(
                command_type="pose", use_relative_mode=True, ik_method="dls"
            ),
            scale=0.5,
        )
        self.actions.right_arm_action = DifferentialInverseKinematicsActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_joint[1-7]"],
            body_name="openarm_right_hand",
            controller=DifferentialIKControllerCfg(
                command_type="pose", use_relative_mode=True, ik_method="dls"
            ),
            scale=0.5,
        )

        # Binary gripper action terms — open/close per arm.
        # OpenArm finger joints are prismatic; "open" pushes fingers outward, "close" pulls in.
        # The exact open/close values come from the joint limits — leaving the defaults here
        # and tuning during the smoke test.
        self.actions.left_gripper_action = BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_finger_joint.*"],
            open_command_expr={"openarm_left_finger_joint.*": 0.044},
            close_command_expr={"openarm_left_finger_joint.*": 0.0},
        )
        self.actions.right_gripper_action = BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_finger_joint.*"],
            open_command_expr={"openarm_right_finger_joint.*": 0.044},
            close_command_expr={"openarm_right_finger_joint.*": 0.0},
        )

        # Teleop devices:
        #   * ``handtracking`` — bimanual hand-tracking via OpenXR. Each hand owns
        #     one Se3Rel retargeter and one gripper retargeter. The OpenXR device
        #     concatenates the four retargeters' outputs into a single 14-dim
        #     action vector matching the env action manager's term order:
        #       [left_arm(6), left_gripper(1), right_arm(6), right_gripper(1)]
        #   * ``keyboard`` — Se3Keyboard wrapped to drive the right arm only;
        #     left arm holds its default joint pose. Smoke-test path.
        self.teleop_devices = DevicesCfg(
            devices={
                "keyboard": BimanualKeyboardRightArmCfg(
                    pos_sensitivity=0.05,
                    rot_sensitivity=0.05,
                    sim_device=self.sim.device,
                ),
                "handtracking": OpenXRDeviceCfg(
                    retargeters=[
                        Se3RelRetargeterCfg(
                            bound_hand=DeviceBase.TrackingTarget.HAND_LEFT,
                            zero_out_xy_rotation=True,
                            use_wrist_rotation=False,
                            use_wrist_position=True,
                            delta_pos_scale_factor=10.0,
                            delta_rot_scale_factor=10.0,
                            sim_device=self.sim.device,
                        ),
                        GripperRetargeterCfg(
                            bound_hand=DeviceBase.TrackingTarget.HAND_LEFT,
                            sim_device=self.sim.device,
                        ),
                        Se3RelRetargeterCfg(
                            bound_hand=DeviceBase.TrackingTarget.HAND_RIGHT,
                            zero_out_xy_rotation=True,
                            use_wrist_rotation=False,
                            use_wrist_position=True,
                            delta_pos_scale_factor=10.0,
                            delta_rot_scale_factor=10.0,
                            sim_device=self.sim.device,
                        ),
                        GripperRetargeterCfg(
                            bound_hand=DeviceBase.TrackingTarget.HAND_RIGHT,
                            sim_device=self.sim.device,
                        ),
                    ],
                    sim_device=self.sim.device,
                    xr_cfg=self.xr,
                ),
            }
        )
