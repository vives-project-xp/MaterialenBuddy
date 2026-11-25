"""Real robot, navigation: hardware_base (robot_state_publisher + LD19 + relays) + map_server + AMCL + Nav2 + RViz.

The map is created beforehand with `mapping.launch.py` (teleoperation) and saved with scripts/save_map.sh.
Here the robot navigates on it with AMCL.

AMCL needs to know where the robot is at startup. By default (set_initial_pose:=true) it places it at
initial_x/y/yaw, which defaults to 0,0,0 = the map origin, i.e. the point the map was started from
(the dock): put the robot there before launching. If it is somewhere else, pass initial_x/y/yaw, or
set_initial_pose:=false and use "2D Pose Estimate" in RViz.

Each include applies the namespace on its own: this launch does NOT wrap them in another one.

Usage:
    ros2 launch mrobot_bringup navigation.launch.py map_yaml:=$HOME/MaterialenBuddy/robot_code/maps/map1.yaml \\
        lidar_port:=/dev/ldlidar
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
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
            "lidar_port": LaunchConfiguration("lidar_port"),
            "lidar_baudrate": LaunchConfiguration("lidar_baudrate"),
            "laser_scan_dir": LaunchConfiguration("laser_scan_dir"),
            "laser_yaw": LaunchConfiguration("laser_yaw"),
        }.items(),
    )

    # odom_topic "odom_reliable": the Create 3 publishes odom BEST_EFFORT and Nav2 asks for RELIABLE;
    # the odom_relay started by hardware_base republishes it on that topic.
    nav = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_dir, "nav.launch.py")),
        launch_arguments={
            "robot_namespace": namespace,
            "use_sim_time": use_sim_time,
            "map_yaml": LaunchConfiguration("map_yaml"),
            "rviz": LaunchConfiguration("rviz"),
            "set_initial_pose": LaunchConfiguration("set_initial_pose"),
            "initial_x": LaunchConfiguration("initial_x"),
            "initial_y": LaunchConfiguration("initial_y"),
            "initial_yaw": LaunchConfiguration("initial_yaw"),
            "odom_topic": "odom_reliable",
            "live_mapping": LaunchConfiguration("live_mapping"),
        }.items(),
    )

    return LaunchDescription(
        [
            robot_namespace_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "map_yaml", description="Absolute path to the map .yaml."),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument(
                "lidar_port",
                default_value="/dev/ttyUSB0",
                description="LD19 serial port; e.g. /dev/ldlidar.",
            ),
            DeclareLaunchArgument("lidar_baudrate", default_value="230400"),
            DeclareLaunchArgument(
                "laser_scan_dir", default_value="true", description="true|false"),
            DeclareLaunchArgument(
                "laser_yaw", default_value="0.0", description="LD19 rotation (rad)."),
            DeclareLaunchArgument(
                "set_initial_pose",
                default_value="true",
                description="true = AMCL starts at initial_x/y/yaw (by default the map origin, the dock). "
                "false = set the pose with 2D Pose Estimate in RViz.",
            ),
            DeclareLaunchArgument(
                "live_mapping", default_value="true",
                description="true = slam_toolbox keeps updating the map while navigating; false = static map + AMCL."),
            DeclareLaunchArgument("initial_x", default_value="0.0"),
            DeclareLaunchArgument("initial_y", default_value="0.0"),
            DeclareLaunchArgument("initial_yaw", default_value="0.0"),
            nav,  # first: validates map_yaml before any process starts
            hardware,
        ]
    )
