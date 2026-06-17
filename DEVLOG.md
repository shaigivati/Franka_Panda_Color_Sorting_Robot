# Development Notes

## Date

2025-06-17

## Work Completed

### Created a New Fork

Created a personal fork of the project to continue development independently and keep custom changes separated from the original repository.

Repository:

```text
https://github.com/MechaMind-Labs/Franka_Panda_Color_Sorting_Robot
```

---

### Migrated the Project to Gazebo (gz_sim)

Completed the migration from the older Ignition-based setup to the current Gazebo stack.

Updated the robot hardware interface to use:

```xml
<plugin>gz_ros2_control/GazeboSimSystem</plugin>
```

Verified that the robot loads correctly and that ROS2 controllers communicate with Gazebo through `gz_ros2_control`.

---

### Removed MoveIt from the Launch Flow

Removed the MoveIt-based execution path from the launch sequence.

The project no longer depends on:

```bash
ros2 run pymoveit2 pick_and_place.py
```

for robot motion execution.

This simplifies the runtime architecture and prepares the project for direct policy-based control.

---

### Investigated the Robot Control Path

Identified the controller responsible for arm motion:

Configuration:

```text
src/panda_controller/config/panda_controllers.yaml
```

Launch/spawning:

```text
src/panda_controller/launch/controller.launch.py
```

Verified that the arm controller subscribes to:

```text
/arm_controller/joint_trajectory
```

using:

```bash
ros2 topic info /arm_controller/joint_trajectory -v
```

Result:

```text
Publisher count: 0
Subscription count: 1

Node name: arm_controller
```

This confirms that:

```text
Publisher
    ↓
/arm_controller/joint_trajectory
    ↓
arm_controller
    ↓
gz_ros2_control
    ↓
Gazebo Panda Robot
```

is the correct command path for controlling the robot.

---

## TODO

### Implement a Policy Controller Node

Create a ROS2 node that:

1. Reads the current robot state from:

```text
/joint_states
```

2. Builds the observation vector required by the policy.

3. Runs policy inference.

4. Publishes robot commands to:

```text
/arm_controller/joint_trajectory
```

5. Publishes gripper commands to:

```text
/gripper_controller/joint_trajectory
```

6. Becomes the single source of robot motion commands.
