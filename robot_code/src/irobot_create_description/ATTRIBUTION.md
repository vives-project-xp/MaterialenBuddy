# Provenance and licenses

This package mixes official iRobot files (unmodified) and the project's own files.

## Official iRobot files (BSD 3-Clause, (c) 2021 iRobot Corporation)

- **Origin:** <https://github.com/iRobotEducation/create3_sim> (branch `jazzy`),
  folder `irobot_create_common/irobot_create_description`.
- **License:** see the `LICENSE` file in this package (it must be kept in any redistribution).
- **Files:**
  - `meshes/` (all the meshes).
  - `urdf/create3.urdf.xacro`, `bumper`, `button`, `caster`, `common_properties`, `wheel`, `wheel_drop`
    and `wheel_with_wheeldrop` (`*.urdf.xacro`).
  - `urdf/dock/` and `urdf/sensors/`, except `lidar_ld19.urdf.xacro`.
- **Modifications:** none. If an official file is ever edited, note it here.

## Own files (Apache-2.0)

- `urdf/create3_ld19.urdf.xacro`: joins the Create 3 with the LD19 LiDAR.
- `urdf/sensors/lidar_ld19.urdf.xacro`: LD19 macro with the datasheet values.
- `launch/display.launch.py` and `rviz/`.
