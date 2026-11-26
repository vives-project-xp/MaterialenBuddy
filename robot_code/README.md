# robot_code

ROS 2 code for the MaterialenBuddy robot: an **iRobot Create 3** with a **Raspberry Pi 5** and a 2D LiDAR (**LD19** or **SLAMTEC RPLIDAR C1**),
running **ROS 2 Jazzy**.

The robot does three things:

1. **Maps** a space with `slam_toolbox`, driven by teleoperation.
2. **Navigates** autonomously with Nav2, on a fixed map (AMCL) or a live one (`slam_toolbox`). Goals are given from RViz.
3. It is **simulated** first in Gazebo Harmonic.

## Structure

```text
robot_code/
├── maps/                          saved maps (the contents are not versioned)
├── scripts/
│   ├── setup_pi.sh                prepares the Pi: rosdep, ROS 2 network, udev rule. Does not build
│   ├── save_map.sh                saves the map that slam_toolbox is building
│   └── rviz_remote.sh             opens RViz on your PC for the robot running on the Pi
└── src/
    ├── irobot_create_description/ Create 3 URDF (official) + LiDAR models (own) + launch to view it in RViz
    ├── mrobot_bringup/            real robot: LiDAR, mapping and navigation
    ├── mrobot_simulation/         Gazebo Harmonic
    ├── irobot_create_control/     wheel controller configuration (simulation only; minimal copy)
    ├── ldlidar_stl_ros2/          official LD19 driver (a copy, no need to clone it)
    └── sllidar_ros2/              official RPLIDAR driver (a copy, no need to clone it)
```

The `mrobot_` prefix marks this project's own packages; the iRobot packages keep their original name
because the official URDFs reference it.

## How it fits together

- The **Create 3 runs its own firmware**: it is reached over the network and lives in the `/r2` namespace
  (`/r2/odom`, `/r2/tf`, `/r2/cmd_vel`...). This code **does not start it**.
- The **Raspberry Pi** runs this workspace: it reads the LiDAR over USB, publishes the robot model and runs `slam_toolbox` or
  Nav2. The Pi and the Create 3 must use the same `ROS_DOMAIN_ID` and the same RMW.
- **RViz** is best opened on your PC (`scripts/rviz_remote.sh`), not on the Pi.

The whole stack hangs from the robot namespace (`/r2/scan`, `/r2/map`...). It is changed with the
`robot_namespace:=` argument or the `CREATE3_ROBOT_NAMESPACE` environment variable. The simulation runs **without a namespace**.

## Requirements

- Ubuntu with **ROS 2 Jazzy**, `git`, `colcon` and `rosdep`.
- For the simulation (on a PC): see [Simulation](#simulation-on-a-pc).

## Installation on the Raspberry Pi

```bash
cd robot_code
scripts/setup_pi.sh                       # rosdep, ROS_DOMAIN_ID / RMW, udev rule /dev/lidar
colcon build --symlink-install --parallel-workers 2 --packages-up-to mrobot_bringup
source install/setup.bash
```

`setup_pi.sh` does not build: you run `colcon build` yourself. `--packages-up-to` leaves the simulation out and
`--parallel-workers 2` keeps the Pi from running out of RAM. Script options: `--skip-udev`, `--skip-net`, `--domain-id N`,
`--rmw NAME` (see `scripts/setup_pi.sh --help`).

After `setup_pi.sh`, log out and back in (`dialout` group), and configure the **same RMW and domain on the Create 3**
(its web UI, *Application > ROS 2*). Restart its application after changing them. To check the connection:

```bash
ros2 topic list | grep -E '/r2/(odom|cmd_vel)'
```

## Choosing the LiDAR

| `lidar_model` | Sensor | Driver |
| --- | --- | --- |
| `ld19` (default) | LDRobot LD19 | `ldlidar_stl_ros2` |
| `rplidar_c1` | SLAMTEC RPLIDAR C1 | `sllidar_ros2` |

Pass `lidar_model:=rplidar_c1` to the launch files, or set it once:

```bash
echo 'export LIDAR_MODEL=rplidar_c1' >> ~/.bashrc
```

Connect only one USB LiDAR at a time: both use `/dev/lidar`. If you already ran an older `setup_pi.sh`, run it
again to create that symlink, then rebuild.

**RPLIDAR C1 orientation:** the profile uses `laser_yaw` = π, which assumes the arrow on top points to the robot
front (cable to the back). Check it in RViz with an object in front of the robot, then one on its left.

**Adding a LiDAR:** install its driver; create `mrobot_bringup/config/lidars/<name>.yaml` and
`irobot_create_description/urdf/sensors/lidar_<name>.urdf.xacro` (copy existing ones; the macro must be called
`lidar` and create `laser_frame`); add the driver to `mrobot_bringup/package.xml` and, if needed, a udev rule;
rebuild. The driver must publish a `LaserScan` with a positive `angle_increment`. Nav2 costmap ranges stay in
`nav2_params.yaml`: lower them for a shorter-range sensor.

## Using the real robot

### 1. Map

On the Pi:

```bash
ros2 launch mrobot_bringup mapping.launch.py lidar_model:=rplidar_c1 rviz:=false
```

On your PC, to see the map:

```bash
scripts/rviz_remote.sh mapping
```

Drive the robot with the keyboard (from the Pi or your PC):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/r2/cmd_vel
```

When the map is complete, save it (with `mapping.launch.py` still running):

```bash
scripts/save_map.sh map_name                      # on the machine where slam_toolbox runs
scripts/save_map.sh map_name --pull user@pi-host  # if you run it from another machine
```

This generates four files in `maps/`: `map_name.yaml` and `map_name.pgm` (the image, for navigating) and `map_name.posegraph` and
`map_name.data` (the slam_toolbox pose graph). They are local files: they are not pushed to the repository.

### 2. Navigate

There are two modes, selected with `live_mapping`. In both, the goal is given with RViz's **2D Goal Pose** tool.

| | Fixed map | Live map |
| --- | --- | --- |
| Argument | `live_mapping:=false` | `live_mapping:=true` (default) |
| Localization | `map_server` + AMCL | `slam_toolbox` |
| Saved map is updated while navigating | No (new obstacles are handled by the Nav2 costmaps) | Yes, in memory |
| Initial pose | Launch arguments or **2D Pose Estimate** | Launch arguments only |
| Files needed in `maps/` | `.yaml` and `.pgm` | `.yaml`, `.posegraph` and `.data` |

Run the launch commands on the Pi, from `robot_code/`. On your PC, open RViz with `scripts/rviz_remote.sh navigation`.

#### Fixed map

Use this mode when the robot can start anywhere and the environment does not need to be remapped.

```bash
ros2 launch mrobot_bringup navigation.launch.py map_yaml:=$PWD/maps/map1.yaml lidar_model:=rplidar_c1 rviz:=false \
  live_mapping:=false set_initial_pose:=false
```

In RViz:

1. Click **2D Pose Estimate**, click the robot's position on the map and drag towards where its front is facing.
   Until you do this, warnings about the missing transform to `map` are expected.
2. Check that the LiDAR points line up with the walls. If they do not, repeat the estimate.
3. Drive and turn the robot slowly with the keyboard so AMCL can refine the pose.
4. Send the goal with **2D Goal Pose**.

If the robot always starts at the map origin, facing the same way as when you started mapping, you can leave out
`set_initial_pose:=false`: it then starts at `initial_x/y/yaw` (`0 0 0` by default).

#### Live map

Use this mode to navigate and keep updating the map at the same time. **The initial pose must be correct:** otherwise
new scans can be added in the wrong place and corrupt the map. **2D Pose Estimate** does not correct the pose in this mode.

**Starting at the map origin:** put the robot where you started mapping (normally the dock), facing the same way, and run:

```bash
ros2 launch mrobot_bringup navigation.launch.py map_yaml:=$PWD/maps/map1.yaml lidar_model:=rplidar_c1 rviz:=false \
  live_mapping:=true
```

**Starting somewhere else:** find the pose with AMCL first.

1. Start the [fixed map](#fixed-map) mode, set the pose and drive until the LiDAR points line up with the walls.
2. Stop the robot and, before closing the launch, read its pose:

   ```bash
   ros2 topic echo /r2/amcl_pose --once --qos-durability transient_local --qos-reliability reliable
   ```

3. Calculate the yaw in radians, replacing `Z` and `W` with `orientation.z` and `orientation.w`:

   ```bash
   python3 -c "import math; print(2*math.atan2(Z, W))"
   ```

4. Close the launch **without moving the robot** and start the live mode with your values (these are an example):

   ```bash
   ros2 launch mrobot_bringup navigation.launch.py map_yaml:=$PWD/maps/map1.yaml lidar_model:=rplidar_c1 rviz:=false \
     live_mapping:=true initial_x:=1.25 initial_y:=-0.40 initial_yaw:=1.57
   ```

5. Before sending a goal, check in RViz that the LiDAR points line up with the map. If they do not, close the launch
   and do not save that map.

The updates are not saved automatically. To keep them, save the map while the launch is running, with a new name so the
original is preserved:

```bash
scripts/save_map.sh map2
```

### Useful arguments

| Argument | Where | What for |
| --- | --- | --- |
| `lidar_model` | all launches, simulation | LiDAR profile: `ld19` or `rplidar_c1` (default: `LIDAR_MODEL` or `ld19`) |
| `lidar_port` | mapping, navigation | Serial port, if it is not `/dev/lidar` (e.g. `/dev/ttyUSB0`) |
| `laser_yaw` | mapping, navigation | Overrides the profile rotation (rad). `-1.5707963` was used with the real LD19 |
| `robot_namespace` | all | Robot namespace (default `r2`; empty = none) |
| `rviz` | all | `false` to not open RViz (on the Pi) |
| `live_mapping` | navigation | `true` (default): [live map](#live-map); `false`: [fixed map](#fixed-map) |
| `map_yaml` | navigation | Absolute path to the map `.yaml` (required) |

## Simulation (on a PC)

No Create 3, Raspberry Pi or physical LiDAR is needed: both the robot and the LiDAR are simulated.

### Required software

| Software | Package | What for |
| --- | --- | --- |
| **Ubuntu 24.04** | — | Base system for ROS 2 Jazzy |
| **ROS 2 Jazzy** | `ros-jazzy-desktop` | ROS 2, including RViz |
| **Gazebo Harmonic** | `ros-jazzy-ros-gz` | Simulator and ROS bridge (no separate Gazebo install needed) |
| **Gazebo control** | `ros-jazzy-gz-ros2-control` | Connects `ros2_control` to the simulated robot |
| **Controllers** | `ros-jazzy-ros2-controllers`, `ros-jazzy-controller-manager` | Drive the wheels and publish odometry |
| **SLAM Toolbox** | `ros-jazzy-slam-toolbox` | Mapping |
| **Nav2** | `ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup` | Autonomous navigation |
| **Robot model** | `ros-jazzy-xacro`, `ros-jazzy-robot-state-publisher` | Load the model and publish its transforms |
| **Teleoperation** | `ros-jazzy-teleop-twist-keyboard` | Drive the robot with the keyboard |
| **Tools** | `git`, `python3-colcon-common-extensions`, `python3-rosdep` | Get the code, install dependencies and build |

On another Ubuntu version, you can use an Ubuntu 24.04 container, for example with distrobox:

```bash
distrobox create --name jazzy --image ubuntu:24.04
distrobox enter jazzy
```

### Installation

First [set up the ROS 2 Jazzy apt repository](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html), then:

```bash
sudo apt update
sudo apt install git ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-controllers ros-jazzy-controller-manager ros-jazzy-slam-toolbox \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher ros-jazzy-teleop-twist-keyboard \
  python3-colcon-common-extensions python3-rosdep
```

### Build

From `robot_code/`:

```bash
source /opt/ros/jazzy/setup.bash
sudo rosdep init                          # first time only
rosdep update
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install --packages-select irobot_create_description irobot_create_control mrobot_bringup mrobot_simulation
source install/setup.bash
```

Only these four packages are needed. The LiDAR drivers (`ldlidar_stl_ros2`, `sllidar_ros2`) are for the real robot.

### Run

In every new terminal (inside the container, if you use one), from `robot_code/`:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Map the world:

```bash
ros2 launch mrobot_simulation sim.launch.py                              # map
ros2 run teleop_twist_keyboard teleop_twist_keyboard                     # in another terminal
scripts/save_map.sh room --namespace ''                                  # in a third one; the simulation does not use a namespace
```

Then close the mapping simulation and navigate on the saved map:

```bash
ros2 launch mrobot_simulation sim.launch.py nav:=true map_yaml:=$PWD/maps/room.yaml
```

Other arguments: `headless:=true` (no Gazebo GUI), `x`, `y`, `yaw` (initial pose) and `world` (another `.sdf` world).
The default world is an 8x8 m room with a divider wall and obstacles.

## Things that are not obvious

- **`scan_resampler`**: the number of readings per revolution of the driver can differ from the profile (the LD19 varies between
  ~500 and 504), and `slam_toolbox` requires a fixed number. The node publishes `scan` with the profile's `num_beams`, taken from `scan_raw`. It is not needed in simulation.
- **`odom_relay`**: the Create 3 publishes `odom` with *best effort* QoS and Nav2 asks for *reliable*; the node republishes it on
  `odom_reliable`. Real robot only.
- **`cmd_vel_stamper`**: Jazzy's `diff_drive_controller` receives `TwistStamped`, but the teleop and Nav2 publish
  `Twist`. Simulation only.
- **`irobot_create_control`**: the official URDF references it when `gazebo:=ignition` is used. It is only needed in simulation.
- **The Pi's model includes the full Create 3 URDF**, not a minimal one. The Create 3 also publishes its own frames:
  check that there are no duplicate transforms (`ros2 topic echo /r2/tf_static`).

## Troubleshooting

Places where something is most likely to need adjusting:

- **Model (PC):** `ros2 launch irobot_create_description display.launch.py`. `rviz/model.rviz` still has to be created from RViz.
- **LiDAR driver build and serial port:** `ls -l /dev/lidar`; if it does not exist, run `lsusb` and check the udev rule identifier.
- **The scan comes out rotated or mirrored:** adjust `laser_yaw`; for mirroring, `laser_scan_dir` (LD19) or `inverted`
  (RPLIDAR) in the LiDAR profile.
- **`slam_toolbox` does not activate:** it is a lifecycle node; the launch configures and activates it. Check `ros2 lifecycle get /r2/slam_toolbox`.
- **The `.rviz` files** are written by hand: if something is not visible, adjust it in RViz and save the configuration.
- **Simulation:** that the *spawners* do not time out while the meshes load, that `/odom`, `/tf` and
  `/joint_states` exist, and that the meshes are found (`GZ_SIM_RESOURCE_PATH`).

## Third-party code and licenses

| Package | Origin | License |
| --- | --- | --- |
| `irobot_create_description` (official URDF and meshes) | [iRobotEducation/create3_sim](https://github.com/iRobotEducation/create3_sim), branch `jazzy` | BSD-3-Clause |
| `irobot_create_control` | same (minimal copy) | BSD-3-Clause |
| `ldlidar_stl_ros2` | [ldrobotSensorTeam/ldlidar_stl_ros2](https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2) (with one modification) | MIT |
| `sllidar_ros2` | [Slamtec/sllidar_ros2](https://github.com/Slamtec/sllidar_ros2) (with one modification) | BSD |

The details of what was copied and what was modified are in `VENDORED.md` (`ldlidar_stl_ros2`, `sllidar_ros2`, `irobot_create_control`) and in
`ATTRIBUTION.md` (`irobot_create_description`). The project's own code is Apache-2.0.
