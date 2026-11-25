# Third-party code included in the repository

Minimal copy of the `irobot_create_control` package from the official iRobot Create 3 simulator.
The official URDFs in `irobot_create_description` reference it (`$(find irobot_create_control)/config/control.yaml`)
to configure the wheel controller in Gazebo.

- **Origin:** <https://github.com/iRobotEducation/create3_sim> (branch `jazzy`),
  folder `irobot_create_common/irobot_create_control`
- **Copied commit:** `6c305843afcfe094bf8eb2a0c6997f531e526b9d`
- **License:** BSD 3-Clause, (c) 2021 iRobot Corporation (see `LICENSE`; it must be kept)
- **Copied:** `config/control.yaml` (unchanged), `package.xml` and `LICENSE`.

## Changes with respect to the original

1. `CMakeLists.txt`: it only installs `config` (`launch` was removed because it was not copied) and the tests were dropped.
2. `package.xml`: the `ros2launch` and `rsl` dependencies and the test dependencies were removed; only the `launch` folder used them.
3. `launch/include/control.py` was not copied: the controllers are started from
   `mrobot_simulation/launch/sim.launch.py`.

## Warning: obsolete parameters in control.yaml

The YAML was written for an older version of `diff_drive_controller`. In Jazzy, `use_stamped_vel`, `publish_cmd`,
`publish_wheel_data` and `preserve_turning_radius` no longer exist: ROS ignores them.
What does matter in Jazzy: the controller receives `TwistStamped` on `diffdrive_controller/cmd_vel`
(that is why the simulation includes `cmd_vel_stamper.py`).
