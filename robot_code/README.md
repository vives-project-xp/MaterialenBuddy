# robot_code

ROS 2 code for the MaterialenBuddy robot: an **iRobot Create 3** with a **Raspberry Pi 5** and an **LD19 LiDAR**,
running **ROS 2 Jazzy**.

The robot does three things:

1. **Maps** a space with `slam_toolbox`, driven by teleoperation.
2. **Navigates** autonomously on the saved map, with AMCL and Nav2 (goals are given from RViz).
3. It is **simulated** first in Gazebo Harmonic.

> **Status: none of this has been tested yet.** The code is written and reviewed, and the scripts and
> configuration files pass syntax checks, but it has not been run with ROS 2, Gazebo or the
> robot. See [First run](#first-run-what-to-check).

## Structure

```text
robot_code/
├── maps/                          saved maps (the contents are not versioned)
├── scripts/
│   ├── setup_pi.sh                prepares the Pi: rosdep, ROS 2 network, udev rule. Does not build
│   ├── save_map.sh                saves the map that slam_toolbox is building
│   └── rviz_remote.sh             opens RViz on your PC for the robot running on the Pi
└── src/
    ├── irobot_create_description/ Create 3 URDF (official) + LD19 (own) + launch to view it in RViz
    ├── mrobot_bringup/            real robot: LiDAR, mapping and navigation
    ├── mrobot_simulation/         Gazebo Harmonic
    ├── irobot_create_control/     wheel controller configuration (simulation only; minimal copy)
    └── ldlidar_stl_ros2/          official LD19 driver (a copy, no need to clone it)
```

The `mrobot_` prefix marks this project's own packages; the iRobot packages keep their original name
because the official URDFs reference it.

## How it fits together

- The **Create 3 runs its own firmware**: it is reached over the network and lives in the `/r2` namespace
  (`/r2/odom`, `/r2/tf`, `/r2/cmd_vel`...). This code **does not start it**.
- The **Raspberry Pi** runs this workspace: it reads the LD19 over USB, publishes the robot model and runs `slam_toolbox` or
  Nav2. The Pi and the Create 3 must use the same `ROS_DOMAIN_ID` and the same RMW.
- **RViz** is best opened on your PC (`scripts/rviz_remote.sh`), not on the Pi.

The whole stack hangs from the robot namespace (`/r2/scan`, `/r2/map`...). It is changed with the
`robot_namespace:=` argument or the `CREATE3_ROBOT_NAMESPACE` environment variable. The simulation runs **without a namespace**.

## Requirements

- Ubuntu with **ROS 2 Jazzy**, `git`, `colcon` and `rosdep`.
- For the simulation (on a PC): `ros-jazzy-ros-gz`, `ros-jazzy-gz-ros2-control` and `ros-jazzy-ros2-controllers`.

## Installation on the Raspberry Pi

```bash
cd robot_code
scripts/setup_pi.sh                       # rosdep, ROS_DOMAIN_ID / RMW, udev rule /dev/ldlidar
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

## Using the real robot

### 1. Map

On the Pi:

```bash
ros2 launch mrobot_bringup mapping.launch.py lidar_port:=/dev/ldlidar rviz:=false
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
scripts/save_map.sh map1                           # on the machine where slam_toolbox runs
scripts/save_map.sh map1 --pull user@pi-host       # if you run it from another machine
```

This generates four files in `maps/`: `map1.yaml` and `map1.pgm` (the image, for navigating) and `map1.posegraph` and
`map1.data` (the slam_toolbox pose graph). They are local files: they are not pushed to the repository.

### 2. Navigate

Put the robot at the point you mapped from (the map origin, normally the dock) and, on the Pi:

```bash
ros2 launch mrobot_bringup navigation.launch.py map_yaml:=$PWD/maps/map1.yaml lidar_port:=/dev/ldlidar rviz:=false
```

On your PC: `scripts/rviz_remote.sh navigation`. The goal is given with RViz's **2D Goal Pose** tool.

AMCL starts at `initial_x/y/yaw` (`0 0 0` by default, the map origin). If the robot is somewhere else, pass those
arguments or `set_initial_pose:=false` and use **2D Pose Estimate** in RViz.

### Useful arguments

| Argument | Where | What for |
|---|---|---|
| `lidar_port` | mapping, navigation | LD19 port (`/dev/ldlidar` with the udev rule; `/dev/ttyUSB0` without it) |
| `laser_scan_dir` | mapping, navigation | LD19 scan direction: flip it if the scan comes out inverted |
| `laser_yaw` | mapping, navigation | Sensor rotation relative to the robot front (rad). `-1.5707963` was used with the real sensor |
| `robot_namespace` | all | Robot namespace (default `r2`; empty = none) |
| `rviz` | all | `false` to not open RViz (on the Pi) |
| `map_yaml` | navigation | Absolute path to the map `.yaml` (required) |

## Simulation (on a PC)

```bash
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source install/setup.bash
ros2 launch mrobot_simulation sim.launch.py                              # map
ros2 run teleop_twist_keyboard teleop_twist_keyboard                     # in another terminal
scripts/save_map.sh room --namespace ''                                  # the simulation does not use a namespace
ros2 launch mrobot_simulation sim.launch.py nav:=true map_yaml:=$PWD/maps/room.yaml
```

Other arguments: `headless:=true` (no Gazebo GUI), `x`, `y`, `yaw` (initial pose) and `world` (another `.sdf` world).
The default world is an 8x8 m room with a divider wall and obstacles.

## Things that are not obvious

- **`scan_resampler`**: the real LD19 delivers between ~500 and 504 readings per revolution, and `slam_toolbox` requires a fixed number.
  The node publishes `scan` with always 500 beams, taken from `scan_raw`. It is not needed in simulation.
- **`odom_relay`**: the Create 3 publishes `odom` with *best effort* QoS and Nav2 asks for *reliable*; the node republishes it on
  `odom_reliable`. Real robot only.
- **`cmd_vel_stamper`**: Jazzy's `diff_drive_controller` receives `TwistStamped`, but the teleop and Nav2 publish
  `Twist`. Simulation only.
- **`irobot_create_control`**: the official URDF references it when `gazebo:=ignition` is used. It is only needed in simulation.
- **The Pi's model includes the full Create 3 URDF**, not a minimal one. The Create 3 also publishes its own frames:
  check that there are no duplicate transforms (`ros2 topic echo /r2/tf_static`).

## First run: what to check

Places where something is most likely to need adjusting:

- **Model (PC):** `ros2 launch irobot_create_description display.launch.py`. `rviz/model.rviz` still has to be created from RViz.
- **LD19 driver build and serial port:** `ls -l /dev/ldlidar`; if it does not exist, run `lsusb` and check the udev rule identifier.
- **The scan comes out rotated or inverted:** adjust `laser_yaw` and `laser_scan_dir`.
- **`slam_toolbox` does not activate:** it is a lifecycle node; the launch configures and activates it. Check `ros2 lifecycle get /r2/slam_toolbox`.
- **The `.rviz` files** are written by hand and untested: if something is not visible, adjust it in RViz and save the configuration.
- **Simulation:** that the *spawners* do not time out while the meshes load, that `/odom`, `/tf` and
  `/joint_states` exist, and that the meshes are found (`GZ_SIM_RESOURCE_PATH`).

## Third-party code and licenses

| Package | Origin | License |
|---|---|---|
| `irobot_create_description` (official URDF and meshes) | [iRobotEducation/create3_sim](https://github.com/iRobotEducation/create3_sim), branch `jazzy` | BSD-3-Clause |
| `irobot_create_control` | same (minimal copy) | BSD-3-Clause |
| `ldlidar_stl_ros2` | [ldrobotSensorTeam/ldlidar_stl_ros2](https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2) (with one modification) | MIT |

The details of what was copied and what was modified are in `VENDORED.md` (`ldlidar_stl_ros2`, `irobot_create_control`) and in
`ATTRIBUTION.md` (`irobot_create_description`). The project's own code is Apache-2.0.
