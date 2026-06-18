# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Base configuration for the bimanual centrifuge pick-and-place task.

The task: a bimanual OpenArm robot picks a plastic centrifuge tube from the
table and places it into a centrifuge bucket. Both arms are teleoperated; the
task does not prescribe which hand does which step.

This base cfg leaves the robot articulation and action terms ``MISSING`` so
that concrete variants (e.g. IK-rel) can plug in robot-specific bindings.
"""

from dataclasses import MISSING
from importlib.resources import files as _pkg_files

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg, RigidObjectCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.managers import ActionTermCfg as ActionTerm
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import FrameTransformerCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import GroundPlaneCfg, UsdFileCfg
from isaaclab.sim.spawners.meshes.meshes_cfg import MeshCuboidCfg
from isaaclab.utils import configclass

from . import mdp

# Rigid-body-prepared USDs bundled inside the package wheel. ``importlib.resources.files``
# resolves the path correctly for both editable (``pip install -e .``) and built-wheel
# installs. See ``scripts/prepare_assets.py`` for how to regenerate these from raw
# geometry-only originals.
CENTRIFUGE_DATASET_DIR = str(_pkg_files("rpl_openarm_centrifuge") / "assets")


##
# Scene
##


@configclass
class CentrifugeSceneCfg(InteractiveSceneCfg):
    """Scene: ground, light, table, robot pedestal, bimanual robot, tube rack, tube, bucket.

    Geometry tuned so the OpenArm bimanual can comfortably reach the rack and
    bucket from a natural shoulders-above-table pose. World/env frame:
      * Ground plane at z=0.
      * Robot pedestal: 0.413 x 0.413 x 0.579 m cube centred at (-0.62, 0, 0.289)
        so its top is at z=0.578 (preserved from ``aiet_scene.usd``).
      * Table: top at z=0.80 (~0.22 m above the robot base, so the shoulders sit
        above the table top and the hands lower naturally onto it).
      * Robot base mounted on the pedestal top at (-0.62, 0, 0.5786).
      * Tube rack: static fixture on the table at (-0.35, -0.15, 0.80) on the
        robot's right (-y) side — placed as close to the right hand as the
        pedestal allows. The tube starts on top of the rack.
      * Bucket: dynamic rigid body at (-0.20, 0.00, 0.85) on the centre-line,
        receptacle for successful task completion.

    The asymmetric layout (rack on -y, bucket on centre) reflects the
    "right hand picks first, then transports to centre" intended operation
    order. Mirror to +y if you want left-hand-first operation.

    Rack / tube / bucket positions are starting values intended for in-sim
    tuning. The success criterion (tube inside the bucket) is invariant to
    these positions, so retuning doesn't change the task definition.
    """

    # robot: filled in by the concrete variant
    robot: ArticulationCfg = MISSING
    # end-effector frames: filled in by the concrete variant (need to know body names)
    left_ee_frame: FrameTransformerCfg = MISSING
    right_ee_frame: FrameTransformerCfg = MISSING

    # ground
    ground = AssetBaseCfg(
        prim_path="/World/GroundPlane",
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.0, 0.0, 0.0)),
        spawn=GroundPlaneCfg(),
    )

    # dome light
    light = AssetBaseCfg(
        prim_path="/World/light",
        spawn=sim_utils.DomeLightCfg(color=(0.75, 0.75, 0.75), intensity=3000.0),
    )

    # robot pedestal — static cuboid; top at z = 0.289 + 0.579/2 = 0.5785.
    pedestal = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Pedestal",
        init_state=AssetBaseCfg.InitialStateCfg(pos=(-0.62, 0.0, 0.289), rot=(1.0, 0.0, 0.0, 0.0)),
        spawn=MeshCuboidCfg(
            size=(0.413, 0.413, 0.579),
            collision_props=sim_utils.CollisionPropertiesCfg(collision_enabled=True),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.3, 0.3, 0.3)),
        ),
    )

    # table — static cuboid; top at z = 0.0 + 0.80 = 0.80.
    # Footprint chosen so the -x edge (x=-0.4) doesn't overlap the pedestal
    # (whose +x edge is at x=-0.413), leaving a small visual gap.
    table = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.1, 0.0, 0.40), rot=(1.0, 0.0, 0.0, 0.0)),
        spawn=MeshCuboidCfg(
            size=(1.0, 0.6, 0.80),
            collision_props=sim_utils.CollisionPropertiesCfg(collision_enabled=True),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.6, 0.5, 0.4)),
        ),
    )

    # tube rack — static fixture sitting on the table; convexDecomposition
    # collision (already authored in the USD) preserves the wells so the tube
    # can be inserted. Placed on the robot's -y (right) side so the right hand
    # operates first. Positions are starting values for in-sim tuning.
    # x=-0.35 is the closest the rack can sit without intruding into the
    # pedestal (+x face at -0.413, rack half-width 0.0625). y=-0.15 aligns
    # with the right hand's y (-0.153) so the right arm can reach straight
    # forward instead of obliquely.
    rack = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Rack",
        init_state=AssetBaseCfg.InitialStateCfg(pos=(-0.35, -0.15, 0.80), rot=(1.0, 0.0, 0.0, 0.0)),
        spawn=UsdFileCfg(usd_path=f"{CENTRIFUGE_DATASET_DIR}/centrifuge_tube_rack.usd"),
    )

    # plastic centrifuge tube (rigid) — sits on top of the rack at the same xy.
    # Rack top surface is at z=0.878 (rack bottom 0.80 + height 0.078); tube
    # height 0.122 → tube bottom rests on rack top with tube centre at 0.94.
    tube = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Tube",
        init_state=RigidObjectCfg.InitialStateCfg(pos=(-0.35, -0.15, 0.94), rot=(1.0, 0.0, 0.0, 0.0)),
        spawn=UsdFileCfg(
            usd_path=f"{CENTRIFUGE_DATASET_DIR}/centrifuge_tube_big.usd",
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=1,
                max_angular_velocity=1000.0,
                max_linear_velocity=1000.0,
                max_depenetration_velocity=5.0,
                disable_gravity=False,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.05),
        ),
    )

    # centrifuge bucket (rigid — heavy enough to act as a stable receptacle).
    # Placed on the robot's centre-line at ~0.42 m xy from the base.
    bucket = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Bucket",
        init_state=RigidObjectCfg.InitialStateCfg(pos=(-0.20, 0.00, 0.85), rot=(1.0, 0.0, 0.0, 0.0)),
        spawn=UsdFileCfg(
            usd_path=f"{CENTRIFUGE_DATASET_DIR}/centrifuge_bucket_big.usd",
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=1,
                max_angular_velocity=1000.0,
                max_linear_velocity=1000.0,
                max_depenetration_velocity=5.0,
                disable_gravity=False,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.5),
        ),
    )


##
# MDP
##


@configclass
class ActionsCfg:
    """Bimanual action terms — left/right arm IK + left/right gripper binary."""

    left_arm_action: ActionTerm = MISSING
    left_gripper_action: ActionTerm = MISSING
    right_arm_action: ActionTerm = MISSING
    right_gripper_action: ActionTerm = MISSING


@configclass
class ObservationsCfg:
    """Observation specifications for the MDP."""

    @configclass
    class PolicyCfg(ObsGroup):
        """State-only observation group used for record_demos + robomimic IL."""

        # robot proprioception
        joint_pos = ObsTerm(func=mdp.joint_pos_rel)
        joint_vel = ObsTerm(func=mdp.joint_vel_rel)
        actions = ObsTerm(func=mdp.last_action)

        # left end-effector pose
        left_eef_pos = ObsTerm(
            func=mdp.ee_frame_position_in_env_frame,
            params={"ee_frame_cfg": SceneEntityCfg("left_ee_frame")},
        )
        left_eef_quat = ObsTerm(
            func=mdp.ee_frame_orientation,
            params={"ee_frame_cfg": SceneEntityCfg("left_ee_frame")},
        )

        # right end-effector pose
        right_eef_pos = ObsTerm(
            func=mdp.ee_frame_position_in_env_frame,
            params={"ee_frame_cfg": SceneEntityCfg("right_ee_frame")},
        )
        right_eef_quat = ObsTerm(
            func=mdp.ee_frame_orientation,
            params={"ee_frame_cfg": SceneEntityCfg("right_ee_frame")},
        )

        # object poses
        tube_pos = ObsTerm(
            func=mdp.object_position_in_env_frame, params={"asset_cfg": SceneEntityCfg("tube")}
        )
        tube_quat = ObsTerm(func=mdp.object_orientation, params={"asset_cfg": SceneEntityCfg("tube")})
        bucket_pos = ObsTerm(
            func=mdp.object_position_in_env_frame, params={"asset_cfg": SceneEntityCfg("bucket")}
        )
        bucket_quat = ObsTerm(
            func=mdp.object_orientation, params={"asset_cfg": SceneEntityCfg("bucket")}
        )

        def __post_init__(self):
            self.enable_corruption = False
            self.concatenate_terms = False

    policy: PolicyCfg = PolicyCfg()


@configclass
class EventCfg:
    """Reset events — randomize the tube within a small region on each reset."""

    randomize_tube_pose = EventTerm(
        func=mdp.reset_object_uniform,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("tube"),
            "pose_range": {
                "x": (-0.05, 0.05),
                "y": (-0.05, 0.05),
                "yaw": (-0.3, 0.3),
            },
        },
    )


@configclass
class TerminationsCfg:
    """Termination terms."""

    time_out = DoneTerm(func=mdp.time_out, time_out=True)

    # tube fell off the table — table top is at z=0.80, so anything well below
    # that counts as a drop.
    tube_dropped = DoneTerm(
        func=mdp.root_height_below_minimum,
        params={"minimum_height": 0.3, "asset_cfg": SceneEntityCfg("tube")},
    )

    # success — record_demos.py picks this term up by name
    success = DoneTerm(func=mdp.tube_inside_bucket)


##
# Env
##


@configclass
class CentrifugeEnvCfg(ManagerBasedRLEnvCfg):
    """Base env config for bimanual centrifuge pick-and-place."""

    # Scene
    scene: CentrifugeSceneCfg = CentrifugeSceneCfg(num_envs=1, env_spacing=2.5, replicate_physics=False)
    # Basic settings
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    # MDP
    terminations: TerminationsCfg = TerminationsCfg()
    events: EventCfg = EventCfg()

    # unused managers
    commands = None
    rewards = None
    curriculum = None

    def __post_init__(self):
        # general settings
        self.decimation = 5
        self.episode_length_s = 30.0
        # simulation settings (100 Hz physics, rendered every other step)
        self.sim.dt = 0.01
        self.sim.render_interval = 2
        self.sim.physx.bounce_threshold_velocity = 0.01
        self.sim.physx.friction_correlation_distance = 0.00625
        self.sim.physx.gpu_found_lost_aggregate_pairs_capacity = 1024 * 1024 * 4
        self.sim.physx.gpu_total_aggregate_pairs_capacity = 16 * 1024
        # viewer — look at the work area from in front of and above the robot
        self.viewer.eye = (1.2, 1.0, 1.6)
        self.viewer.lookat = (-0.25, 0.0, 0.85)
