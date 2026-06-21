#!/usr/bin/env python3

import time

import onnxruntime as ort
import rclpy
from rclpy.node import Node

from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


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

    def __init__(self):
        super().__init__("policy_controller")

        self.declare_parameter(
            "policy_path",
            "/home/shaigiv/franka_ws/src/panda_controller/policy/policy.onnx",
        )
        self.declare_parameter(
            "arm_command_topic",
            "/panda_arm_controller/joint_trajectory",
        )
        self.declare_parameter(
            "gripper_command_topic",
            "/panda_gripper_controller/joint_trajectory",
        )

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

    def send_initial_pose(self):
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

    def build_observation(self):
        pass

    def run_policy(self, observation):
        pass

    def map_actions(self, actions):
        pass

    def publish_command(self, arm_targets, gripper_targets):
        pass

    def control_loop(self):
        pass


def main(args=None):
    rclpy.init(args=args)
    node = PolicyController()

    node.setup_ros_interfaces()
    node.load_policy()
    node.send_initial_pose()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()