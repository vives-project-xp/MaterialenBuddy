# Third-party code included in the repository

This package is a copy of Slamtec's official RPLIDAR driver, used by the `rplidar_c1` LiDAR profile.
It is included here so it does not have to be cloned separately when setting up the robot.

- **Origin:** <https://github.com/Slamtec/sllidar_ros2> (branch `main`)
- **Copied commit:** `34300099fadfc772965962dec837bf436706188f`
- **License:** BSD, (c) RoboPeak Team and Shanghai Slamtec Co., Ltd. (see `LICENSE`; it must be kept)
- **Excluded:** the `.git` folder.
- **Removed, because it is not needed:** `launch/` and `rviz/` (the manufacturer's examples; ours are in
  `mrobot_bringup`), `scripts/` (example udev rules; the project's `scripts/setup_pi.sh` handles them),
  `README.md` and the two `.png` images. All the driver and SDK code is kept.

## Changes with respect to the original

1. `CMakeLists.txt`: `install(DIRECTORY launch rviz ...)` was removed, because those folders no longer exist.

Any other change in this package must be noted here.
