# Third-party code included in the repository

This package is a copy of LDRobot's official driver for the LD19 / LD06 / STL27L LiDARs.
It is included here so it does not have to be cloned separately when setting up the robot.

- **Origin:** <https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2> (branch `master`)
- **Copied commit:** `bf668a89baf722a787dadc442860dcbf33a82f5a`
- **License:** MIT, (c) 2020 SHENZHEN LDROBOT CO., LTD. (see `LICENSE`; it must be kept)
- **Excluded:** the `.git` folder and the original's `.gitignore`.
- **Removed, because it is not needed:** `launch/` (the manufacturer's example launch files; ours is in
  `mrobot_bringup`), `rviz2/`, `scripts/` (example udev rules; the project's `scripts/setup_pi.sh`
  handles them) and `README.md`. All the driver code is kept, including LD06 and STL27L support.

## Changes with respect to the original

1. `ldlidar_driver/include/logger/log_module.h`: `#include <pthread.h>` was uncommented.
   Without it, `pthread_mutex_t` is undeclared and the build fails with Ubuntu 24.04's GCC.
2. `CMakeLists.txt`: `install(DIRECTORY launch rviz2 ...)` was removed, because those folders no longer exist.

Any other change in this package must be noted here.
