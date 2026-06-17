

## 📋 Table of Contents

2. [💻 Manual Installation on Local PC](#-manual-installation-on-local-pc)
3. [🎮 Running the Project](#-running-the-project)
4. [⚠️ Troubleshooting](#️-troubleshooting)
5. [📚 References](#-references)

---

# 💻 Manual Installation on Local PC

If you prefer complete control or need to modify the source code, follow this comprehensive setup guide for a local installation.

## Prerequisites

- **Ubuntu 22.04 LTS** (recommended for ROS 2 Humble)
- **16GB+ RAM** (recommended for Gazebo simulation)
- **20GB+ free disk space**
- **Stable internet connection**

---

## 📦 Step 1: Install ROS 2 Humble

### 1.1 Set Locale

```bash
sudo apt update && sudo apt upgrade -y
locale  # check for UTF-8

sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

### 1.2 Setup Sources

```bash
# Add ROS 2 apt repository
sudo apt install software-properties-common -y
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

### 1.3 Install ROS 2 Packages

```bash
sudo apt update
sudo apt install ros-humble-desktop-full -y
```

### 1.4 Environment Setup

```bash
# Source ROS 2 environment
source /opt/ros/humble/setup.bash

# Add to bashrc for automatic sourcing
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 1.5 Install Development Tools

```bash
sudo apt install python3-rosdep python3-colcon-common-extensions python3-pip -y

# Initialize rosdep
sudo rosdep init
rosdep update
```

---

## 🔧 Step 2: Install MoveIt 2 and Dependencies

```bash
sudo apt install -y \
  ros-humble-moveit \
  ros-humble-moveit-common \
  ros-humble-moveit-ros-move-group \
  ros-humble-moveit-ros-planning \
  ros-humble-moveit-ros-planning-interface \
  ros-humble-moveit-visual-tools \
  ros-humble-moveit-configs-utils \
  ros-humble-moveit-setup-assistant \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-gazebo-ros2-control \
  ros-humble-ros-gz \
  ros-humble-cv-bridge \
  ros-humble-image-transport \
  ros-humble-rqt-image-view
```

---

## 📥 Step 3: Install Python Dependencies

```bash
pip3 install --no-cache-dir \
  opencv-python==4.10.0.84 \
  numpy==1.24.4 \
  transforms3d
```

---

## 🏗️ Step 4: Create and Build Workspace

### 4.1 Create Workspace

```bash
mkdir -p ~/panda_ws/src
cd ~/panda_ws
```

### 4.2 Clone the Repository

```bash
cd ~/panda_ws/src
git clone https://github.com/shaigivati/Franka_Panda_Color_Sorting_Robot.git .
```

### 4.3 Install Package Dependencies

```bash
cd ~/panda_ws
rosdep install --from-paths src --ignore-src --skip-keys=opencv_python -r -y
```

### 4.4 Build the Workspace

```bash
colcon build
```

**Note:** Initial build may take 10-15 minutes depending on your system.

### 4.5 Source the Workspace

```bash
source install/setup.bash

# Add to bashrc for convenience
echo "source ~/panda_ws/install/setup.bash" >> ~/.bashrc
```

---

## ✅ Step 5: Verify Installation

Test that all packages are properly installed:

```bash
# Check available packages
ros2 pkg list | grep panda

# Expected output:
# panda_bringup
# panda_controller
# panda_description
# panda_moveit
# panda_vision
```

---

## 🎮 Running the Project

### Complete Pick-and-Place System

Open **two terminal windows**:

#### Terminal 1: Launch System

```bash
source ~/panda_ws/install/setup.bash
ros2 launch panda_bringup pick_and_place.launch.py
```

Wait for all nodes to initialize (~30 seconds)

#### Terminal 2: Start Pick-and-Place

```bash
source ~/panda_ws/install/setup.bash
ros2 run pymoveit2 pick_and_place.py --ros-args -p target_color:=R
```

**Change colors by stopping** (`Ctrl+C`) **and rerunning with different parameter:**

```bash
# For Green objects
ros2 run pymoveit2 pick_and_place.py --ros-args -p target_color:=G

# For Blue objects
ros2 run pymoveit2 pick_and_place.py --ros-args -p target_color:=B
```

---

## 🔍 Useful ROS 2 Commands

### Monitoring and Debugging

```bash
# List all active nodes
ros2 node list

# List all topics
ros2 topic list

# View camera feed
ros2 run rqt_image_view rqt_image_view

# Echo detected colors
ros2 topic echo /detected_color

# Check robot joint states
ros2 topic echo /joint_states

# Monitor gripper state
ros2 topic echo /panda_gripper/joint_states

# View TF tree
ros2 run rqt_tf_tree rqt_tf_tree

# Visualize computation graph
ros2 run rqt_graph rqt_graph
```

### System Diagnostics

```bash
# Check ROS 2 environment
printenv | grep ROS

# Verify MoveIt installation
ros2 pkg list | grep moveit

# Test motion planning
ros2 launch panda_moveit moveit.launch.py
```

---

# ⚠️ Troubleshooting

## Common Issues and Solutions

### 🔴 Build Failures

**Error:** `Package 'xyz' not found` during build

**Solutions:**
```bash
# Update rosdep database
rosdep update

# Reinstall dependencies
cd ~/panda_ws
rosdep install --from-paths src --ignore-src -r -y

# Clean and rebuild
rm -rf build/ install/ log/
colcon build
```

---

### 🔴 Gazebo Won't Start

**Error:** `Gazebo crashes` or `Segmentation fault`

**Solutions:**
```bash
# Reset Gazebo configuration
killall gzserver gzclient
rm -rf ~/.gazebo/

# Check GPU drivers
glxinfo | grep "OpenGL"

# Try software rendering (slower but stable)
export LIBGL_ALWAYS_SOFTWARE=1
ros2 launch panda_bringup pick_and_place.launch.py
```

---

### 🔴 RViz Display Issues

**Error:** `RViz shows black screen` or crashes

**Solutions:**
```bash
# Reset RViz configuration
rm -rf ~/.rviz2/

# Check display
echo $DISPLAY

# For Docker users
xhost +local:docker
```

---

### 🔴 MoveIt Planning Failures

**Error:** `Unable to plan` or `No valid plan found`

**Solutions:**
1. Check if all controllers are active:
   ```bash
   ros2 control list_controllers
   ```

2. Verify robot state in RViz
3. Adjust planning time in configuration
4. Check for collisions in scene

---

### 🔴 Camera Not Publishing

**Error:** No images on `/camera/image_raw` topic

**Solutions:**
```bash
# Check if Gazebo camera plugin loaded
ros2 topic list | grep camera

# Verify camera in Gazebo GUI
# View → World → Models → camera

# Restart launch file
```

---

### 🔴 Color Detection Not Working

**Error:** No objects detected or wrong colors

**Solutions:**
1. Check HSV thresholds in `color_detector.py`
2. Verify lighting in Gazebo
3. Test with `rqt_image_view`:
   ```bash
   ros2 run rqt_image_view rqt_image_view
   ```
4. Adjust camera position/angle

---


## 🐛 Getting Help

If you encounter issues not covered here:

1. **Check logs:**
   ```bash
   ros2 launch panda_bringup pick_and_place.launch.py --log-level debug
   ```

2. **Search existing issues:**
   [GitHub Issues](https://github.com/MechaMind-Labs/Franka_Panda_Color_Sorting_Robot/issues)

3. **Create a new issue** with:
   - System info: `uname -a`, `ros2 --version`
   - Error messages
   - Steps to reproduce

---

# 📂 Project Structure

```
panda_ws/
├── src/
│   ├── panda_description/        # Robot URDF, meshes, visuals
│   ├── panda_controller/         # Joint/gripper controllers
│   ├── panda_moveit/            # MoveIt 2 configuration
│   ├── panda_vision/            # OpenCV color detection
│   ├── panda_bringup/           # Launch files for full system
│   └── pymoveit2/               # Python MoveIt 2 interface
│       └── examples/
│           └── pick_and_place.py  # Main pick-and-place logic
├── build/                        # Build artifacts
├── install/                      # Installed packages
└── log/                         # Build and runtime logs
```

---

# 🧩 Package Overview

| Package | Description | Key Files |
|---------|-------------|-----------|
| **panda_description** | Robot model and visualization | `panda.urdf.xacro`, meshes |
| **panda_controller** | Controller configurations | `panda_controllers.yaml` |
| **panda_moveit** | Motion planning setup | MoveIt configs, SRDF |
| **panda_vision** | Computer vision system | `color_detector.py` |
| **panda_bringup** | System launcher | `pick_and_place.launch.py` |
| **pymoveit2** | High-level control | `pick_and_place.py` |

---

# 🚀 How It Works

## System Architecture

```
Camera Feed → Color Detection → Object Localization
                                        ↓
                                 Motion Planning (MoveIt 2)
                                        ↓
                               Trajectory Execution
                                        ↓
                         Pick Object → Move to Bin → Place
```

## Detailed Workflow

1. **Vision System** continuously monitors the workspace
2. **Color detector** identifies target color and computes 3D position
3. **PyMoveIt2** receives object coordinates
4. **MoveIt 2** plans collision-free trajectory
5. **Robot controller** executes motion
6. **Gripper** closes to grasp object
7. **Motion planner** computes path to sorting bin
8. **Robot** moves to designated area
9. **Gripper** opens to release object
10. **System** returns to home position and repeats

---

# 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
