# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Bimanual OpenArm centrifuge pick-and-place task for Isaac Lab.

A plastic centrifuge tube starts on the table; the goal is to drop it inside
the centrifuge bucket. Designed for human teleoperation + imitation learning
via Isaac Lab's ``scripts/tools/record_demos.py``.

This package self-registers its gym IDs on import:
  * ``Isaac-Centrifuge-Bimanual-OpenArm-IK-Rel-v0`` — IK-Rel + bimanual
    hand-tracking; keyboard wrapped to drive the right arm only.
  * ``Isaac-Centrifuge-Bimanual-OpenArm-IK-Abs-v0`` — IK-Abs + bimanual
    hand-tracking. Recommended for hand-tracking teleop.

A companion ``.pth`` file shipped with the wheel runs ``import
rpl_openarm_centrifuge`` at every Python startup, so the IDs are visible to
``gym.make()`` without any user code changes. As a fallback, explicitly
``import rpl_openarm_centrifuge  # noqa: F401`` before ``gym.make``.
"""

import gymnasium as gym

from . import agents  # noqa: F401

gym.register(
    id="Isaac-Centrifuge-Bimanual-OpenArm-IK-Rel-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.centrifuge_ik_rel_env_cfg:CentrifugeBimanualIkRelEnvCfg",
    },
    disable_env_checker=True,
)

gym.register(
    id="Isaac-Centrifuge-Bimanual-OpenArm-IK-Abs-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.centrifuge_ik_abs_env_cfg:CentrifugeBimanualIkAbsEnvCfg",
    },
    disable_env_checker=True,
)
