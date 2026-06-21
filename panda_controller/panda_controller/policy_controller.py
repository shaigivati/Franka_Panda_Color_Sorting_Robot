#!/usr/bin/env python3

import time

import onnxruntime as ort
import rclpy
from rclpy.node import Node

from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from controller_manager_msgs.srv import ListControllers

import math
import numpy as np
from std_msgs.msg import String

class PolicyController(Node):
    ARM_JOINTS = [
        "panda_joint1", "panda_joint2", "panda_joint3",
        "panda_joint4", "panda_joint5", "panda_joint6", "panda_joint7",
    ]

    GRIPPER_JOINTS = [
        "panda_finger_joint1",
        "panda_finger_joint2",
    ]

    INITIAL_ARM_POSE = [
        0.0, -0.569, 0.0, -2.81, 0.0, 3.037, 0.741,
    ]

    INITIAL_GRIPPER_POSE = [0.04, 0.04]

    ACTION_SCALE = 0.03

    ARM_LOWER_LIMITS = [-2.8973, -1.7628, -2.8973, -3.0718, -2.8973, -0.0175, -2.8973]
    ARM_UPPER_LIMITS = [ 2.8973,  1.7628,  2.8973, -0.0698,  2.8973,  3.7525,  2.8973]

    GRIPPER_LOWER_LIMITS = [0.0, 0.0]
    GRIPPER_UPPER_LIMITS = [0.04, 0.04]

    def __init__(self):
        super().__init__("policy_controller")

        self.declare_parameter("policy_path","/home/shaigiv/franka_ws/src/panda_controller/policy/policy.onnx")
        self.declare_parameter("arm_command_topic", "/arm_controller/joint_trajectory")
        self.declare_parameter("gripper_command_topic", "/gripper_controller/joint_trajectory")

        self.policy_path = self.get_parameter("policy_path").value
        self.arm_command_topic = self.get_parameter("arm_command_topic").value
        self.gripper_command_topic = self.get_parameter("gripper_command_topic").value

        self.policy = None
        self.input_name = None
        self.output_name = None

        self.joint_state = None
        self.last_action = [0.0] * 8

        self.arm_pub = None
        self.gripper_pub = None

        self.red_object_position = None

    def setup_ros_interfaces(self):
        self.create_subscription(
            JointState,
            "/joint_states",
            self.on_joint_state,
            10,
        )

        self.arm_pub = self.create_publisher(
            JointTrajectory,
            self.arm_command_topic,
            10,
        )

        self.gripper_pub = self.create_publisher(
            JointTrajectory,
            self.gripper_command_topic,
            10,
        )

        self.create_subscription(
            String,
            "/color_coordinates",
            self.on_color_coordinates,
            10,
        )

    def on_joint_state(self, msg):
        self.joint_state = msg

    def load_policy(self):
        session = ort.InferenceSession(
            self.policy_path,
            providers=["CPUExecutionProvider"],
        )

        inputs = session.get_inputs()
        outputs = session.get_outputs()

        if len(inputs) != 1:
            raise ValueError(f"Expected 1 policy input, got {len(inputs)}")
        if len(outputs) != 1:
            raise ValueError(f"Expected 1 policy output, got {len(outputs)}")

        input_shape = list(inputs[0].shape)
        output_shape = list(outputs[0].shape)

        if input_shape != [1, 36]:
            raise ValueError(f"Expected input shape [1, 36], got {input_shape}")
        if output_shape != [1, 8]:
            raise ValueError(f"Expected output shape [1, 8], got {output_shape}")

        self.policy = session
        self.input_name = inputs[0].name
        self.output_name = outputs[0].name

        self.get_logger().info(
            f"Loaded policy: {self.input_name}{input_shape} -> "
            f"{self.output_name}{output_shape}"
        )

    def wait_for_active_controllers(self, timeout_sec=15.0):
        client = self.create_client(ListControllers, "/controller_manager/list_controllers")

        if not client.wait_for_service(timeout_sec=timeout_sec):
            self.get_logger().error("controller_manager service not available")
            return False

        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            future = client.call_async(ListControllers.Request())
            rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

            if future.result() is None:
                continue

            controllers = future.result().controller
            states = {c.name: c.state for c in controllers}

            arm_active = states.get("arm_controller") == "active"
            gripper_active = states.get("gripper_controller") == "active"
            jsb_active = states.get("joint_state_broadcaster") == "active"

            if arm_active and gripper_active and jsb_active:
                self.get_logger().info("Controllers are active")
                return True

            time.sleep(0.2)

        self.get_logger().error("Controllers did not become active")
        return False

    def send_initial_pose(self):

        if not self.wait_for_active_controllers():
            return False

        arm_msg = self.build_trajectory(
            self.ARM_JOINTS,
            self.INITIAL_ARM_POSE,
            duration_sec=2.0,
        )
        gripper_msg = self.build_trajectory(
            self.GRIPPER_JOINTS,
            self.INITIAL_GRIPPER_POSE,
            duration_sec=2.0,
        )

        self.arm_pub.publish(arm_msg)
        self.gripper_pub.publish(gripper_msg)
        self.get_logger().info("Sent IsaacLab initial pose")

        timeout_sec = 10.0
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)

            if self.is_initial_pose_reached(tolerance=0.05):
                self.get_logger().info("Initial pose reached")
                return True

        self.get_logger().error("Initial pose timeout")
        return False

    def build_trajectory(self, joint_names, positions, duration_sec):
        msg = JointTrajectory()
        msg.joint_names = list(joint_names)

        point = JointTrajectoryPoint()
        point.positions = list(positions)

        sec = int(duration_sec)
        nanosec = int((duration_sec - sec) * 1e9)
        point.time_from_start = Duration(sec=sec, nanosec=nanosec)

        msg.points.append(point)
        return msg

    def is_initial_pose_reached(self, tolerance=0.05):
        if self.joint_state is None:
            return False

        current = dict(zip(self.joint_state.name, self.joint_state.position))

        targets = {}
        targets.update(zip(self.ARM_JOINTS, self.INITIAL_ARM_POSE))
        targets.update(zip(self.GRIPPER_JOINTS, self.INITIAL_GRIPPER_POSE))

        for joint_name, target in targets.items():
            if joint_name not in current:
                return False

            if abs(current[joint_name] - target) > tolerance:
                return False

        return True

    def on_color_coordinates(self, msg):
        parts = msg.data.split(",")

        if len(parts) != 4:
            return

        color_id = parts[0]

        if color_id != "R":
            return

        try:
            self.red_object_position = [
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
            ]
        except ValueError:
            return

    def build_observation(self):
    # Expected ONNX observation layout:
    # 9 joint positions + 9 joint velocities + 7 object pose
    # + 3 end-effector position + 8 previous actions = 36

        if self.joint_state is None:
            return None

        if self.red_object_position is None:
            return None

        joint_map = dict(zip(self.joint_state.name, self.joint_state.position))
        velocity_map = dict(zip(self.joint_state.name, self.joint_state.velocity))

        joint_names = self.ARM_JOINTS + self.GRIPPER_JOINTS

        joint_positions = []
        joint_velocities = []

        for joint_name in joint_names:
            if joint_name not in joint_map:
                return None

            pos = joint_map[joint_name]
            vel = velocity_map.get(joint_name, 0.0)

            if math.isnan(pos):
                pos = 0.0

            if math.isnan(vel):
                vel = 0.0

            joint_positions.append(pos)
            joint_velocities.append(vel)

        object_pose = [
            self.red_object_position[0],
            self.red_object_position[1],
            0.055, # Detector Z is not reliable; use IsaacLab cube height.
            1.0, 0.0, 0.0, 0.0, # Identity orientation: qw, qx, qy, qz
        ]

        ee_position = [
            0.0,
            0.0,
            0.0,
        ]

        obs = (
            joint_positions
            + joint_velocities
            + object_pose
            + ee_position
            + self.last_action
        )

        if len(obs) != 36:
            self.get_logger().error(f"Observation length is {len(obs)}, expected 36")
            return None
        return np.array([obs], dtype=np.float32)

    def run_policy(self, observation):
        if self.policy is None:
            return None

        outputs = self.policy.run(
            [self.output_name],
            {self.input_name: observation},
        )

        actions = outputs[0][0]

        if len(actions) != 8:
            self.get_logger().error(f"Expected 8 actions, got {len(actions)}")
            return None

        return actions

    def map_actions(self, actions):
    # Policy output is treated as joint-position deltas.
    # ACTION_SCALE controls how large each policy step is.
        if self.joint_state is None:
            return None, None

        current = dict(zip(self.joint_state.name, self.joint_state.position))

        arm_targets = []
        for i, joint_name in enumerate(self.ARM_JOINTS):
            if joint_name not in current:
                return None, None

            target = current[joint_name] + self.ACTION_SCALE * float(actions[i])
            target = float(np.clip(
                target,
                self.ARM_LOWER_LIMITS[i],
                self.ARM_UPPER_LIMITS[i],
            ))
            arm_targets.append(target)

        gripper_action = float(actions[7])
        gripper_delta = self.ACTION_SCALE * gripper_action

        gripper_targets = []
        for i, joint_name in enumerate(self.GRIPPER_JOINTS):
            if joint_name not in current:
                return None, None

            target = current[joint_name] + gripper_delta
            target = float(np.clip(
                target,
                self.GRIPPER_LOWER_LIMITS[i],
                self.GRIPPER_UPPER_LIMITS[i],
            ))
            gripper_targets.append(target)

        self.last_action = [float(x) for x in actions]

        return arm_targets, gripper_targets

    def publish_command(self, arm_targets, gripper_targets):
        arm_msg = self.build_trajectory(
            self.ARM_JOINTS,
            arm_targets,
            duration_sec=0.3,
        )

        gripper_msg = self.build_trajectory(
            self.GRIPPER_JOINTS,
            gripper_targets,
            duration_sec=0.3,
        )

        self.arm_pub.publish(arm_msg)
        self.gripper_pub.publish(gripper_msg)


    def control_loop(self):
        obs = self.build_observation()
        if obs is None:
            return

        actions = self.run_policy(obs)
        if actions is None:
            return

        arm_targets, gripper_targets = self.map_actions(actions)
        if arm_targets is None or gripper_targets is None:
            return

        self.publish_command(arm_targets, gripper_targets)

def main(args=None):
    rclpy.init(args=args)
    node = PolicyController()

    node.setup_ros_interfaces()
    node.load_policy()

    if not node.send_initial_pose():
        node.destroy_node()
        rclpy.shutdown()
        return

    node.create_timer(0.5, node.control_loop)
        
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()