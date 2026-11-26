"""Real robot, mapping: hardware_base (robot_state_publisher + LiDAR + relays) + slam_toolbox + RViz.

The robot is moved with teleoperation:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/r2/cmd_vel
Each include applies the namespace on its own, so this launch does NOT wrap them in another namespace
(see mrobot_namespace.py).

Usage:
    ros2 launch mrobot_bringup mapping.launch.py lidar_model:=rplidar_c1
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from lidar_profile import lidar_model_argument  # noqa: E402
from mrobot_namespace import robot_namespace_argument  # noqa: E402


def generate_launch_description():
    launch_dir = os.path.join(
        get_package_share_directory("mrobot_bringup"), "launch")
    namespace = LaunchConfiguration("robot_namespace")
    use_sim_time = LaunchConfiguration("use_sim_time")

    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            launch_dir, "hardware_base.launch.py")),
        launch_arguments={
            "robot_namespace": namespace,
            "use_sim_time": use_sim_time,
            "lidar_model": LaunchConfiguration("lidar_model"),
            "lidar_port": LaunchConfiguration("lidar_port"),
            "laser_yaw": LaunchConfiguration("laser_yaw"),
        }.items(),
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_dir, "slam.launch.py")),
        launch_arguments={
            "robot_namespace": namespace,
            "use_sim_time": use_sim_time,
            "rviz": LaunchConfiguration("rviz"),
            "lidar_model": LaunchConfiguration("lidar_model"),
        }.items(),
    )

    return LaunchDescription(
        [
            robot_namespace_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            lidar_model_argument(),
            DeclareLaunchArgument(
                "lidar_port", default_value="", description="Empty = the profile value (/dev/lidar)."),
            DeclareLaunchArgument(
                "laser_yaw", default_value="", description="LiDAR rotation (rad). Empty = the profile value."),
            hardware,
            slam,
        ]
    )
