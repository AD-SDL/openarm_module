#!/usr/bin/env python3
"""REST node for the OpenArm bimanual robot."""

from typing import Annotated, Optional

from madsci.common.types.action_types import ActionFailed
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from madsci.common.types.location_types import LocationArgument
from pathlib import Path

from openarm_interface.openarm_interface import OpenArmBimanual


class OpenArmNodeConfig(RestNodeConfig):
    """Configuration for the OpenArm node module."""

    right_can: str = "can0"
    """CAN interface for the right arm."""
    left_can: str = "can1"
    """CAN interface for the left arm."""
    dataset_root: Path


class OpenArmNode(RestNode):
    """A Rest Node object to control the OpenArm bimanual robot."""

    robot: Optional[OpenArmBimanual] = None
    config: OpenArmNodeConfig = OpenArmNodeConfig()
    config_model = OpenArmNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Opens CAN connections and enables both arms."""
        self.robot = OpenArmBimanual(
            right_can=self.config.right_can,
            left_can=self.config.left_can,
        )
        self.robot.initialize()
        self.logger.log_info("OpenArm Node initialized.")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Disables both arms and releases CAN resources."""
        try:
            if self.robot is not None:
                self.robot.shutdown()
                del self.robot
                self.robot = None
        except Exception as err:
            self.logger.log_error(f"Error shutting down the OpenArm Node: {err}")
            raise err

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        print(self.robot)
        try:
            if self.robot is not None:
                return self.robot.get_observation()
        except Exception as err:
                    self.logger.log_error(f"Error shutting down the OpenArm Node: {err}")
                    raise err
    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @action(name="home", description="Move one or both arms to the zero position using cosine easing.")
    def home(
        self,
        right: Annotated[bool, "Home the right arm."] = True,
        left: Annotated[bool, "Home the left arm."] = True,
        speed: Annotated[Optional[float], "Motion speed [0.0-1.0]. 0 = slowest, 1 = fastest. Defaults to interface default."] = None,
    ) -> Optional[ActionFailed]:
        """Move one or both arms smoothly to their zero (home) position."""
        if not right and not left:
            return ActionFailed(errors=["At least one arm must be selected (right and/or left)."])
        try:
            kwargs = {"right": right, "left": left}
            if speed is not None:
                kwargs["speed"] = speed
            self.robot.home(**kwargs)
        except Exception as err:
            return ActionFailed(errors=[f"Home failed: {err}"])
        return None

    @action(name="move_t", description="Move one or both arms to specified joint configurations.")
    def move_to_location(
        self,
        location: Annotated[LocationArgument, "target location"],
        speed: Annotated[Optional[float], "Motion speed [0.0-1.0]. 0 = slowest, 1 = fastest. Defaults to interface default."] = None,
    ) -> Optional[ActionFailed]:
        """Move one or both arms to the specified joint configuration using cosine easing."""
        left_target = {
                    key.removeprefix("left_"): value for key, value in location.representation.items() if key.startswith("left_")
                }
                # Remove "right_" prefix
        right_target = {
                    key.removeprefix("right_"): value for key, value in location.representation.items() if key.startswith("right_")
                }
        left_angles = list(left_target.values()) if left_target else None
        right_angles = list(right_target.values()) if right_target else None
        if right_angles is None and left_angles is None:
            return ActionFailed(errors=["At least one of right_angles or left_angles must be provided."])
        self.robot.move_arms_to_target(right_angles, left_angles, speed)
        return None
    @action
    def replay(self, repo_id: Annotated[str, "lerobot repo id for the episode"], episode: Annotated[int, "lerobot episode number to replay"], fps: int = 30) -> None:
        """replay a pretrained teleop trajectory"""
        self.robot.replay_example(repo_id, episode, self.config.dataset_root, fps)

    @action
    def rollout(self, policy_path: str, task: str, duration: int) -> None:
        self.robot.rollout(policy_path, task, duration)
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def pause(self) -> None:
        """Pause the node."""
        self.logger.log("Pausing node...")
        self.node_status.paused = True
        self.logger.log("Node paused.")
        return True

    def resume(self) -> None:
        """Resume the node."""
        self.logger.log("Resuming node...")
        self.node_status.paused = False
        self.logger.log("Node resumed.")
        return True

    def shutdown(self) -> None:
        """Shutdown the node."""
        self.shutdown_handler()
        return True

    def reset(self) -> None:
        """Reset the node."""
        self.logger.log("Resetting node...")
        result = super().reset()
        self.logger.log("Node reset.")
        return result

    def safety_stop(self) -> None:
        """Emergency stop - disable all motors immediately."""
        self.logger.log("Stopping node...")
        self.node_status.stopped = True
        try:
            if self.robot is not None:
                self.robot.shutdown()
                del self.robot
                self.robot = None
        except Exception as err:
            self.logger.log_error(f"Error during safety stop: {err}")
        self.logger.log("Node stopped.")
        return True


if __name__ == "__main__":
    openarm_node = OpenArmNode()
    openarm_node.start_node()