"""Hardware base: robot_state_publisher (xacro) + LD19 LiDAR driver + scan_resampler.

NOTE: the iRobot Create 3 is NOT launched here. It runs its own firmware and is reached over the network
(Wi-Fi or Ethernet over USB). The Raspberry Pi 5 must use the same ROS_DOMAIN_ID and RMW as the Create 3
(configured in its web UI: Application > ROS 2). The Create 3 lives in the /r2 namespace; the nodes of this
launch are put under the same `robot_namespace` and TF is remapped to <ns>/tf and <ns>/tf_static. The
namespace is applied here ONCE (see mrobot_namespace.py): do not wrap this launch in another namespace.

LD19 driver: LDRobot's `ldlidar_stl_ros2` (executable `ldlidar_stl_ros2_node`). It is built from source in
the workspace (it is included in src/ldlidar_stl_ros2); it is not available through rosdep.

Usage:
    ros2 launch mrobot_bringup hardware_base.launch.py
    ros2 launch mrobot_bringup hardware_base.launch.py laser_yaw:=-1.5707963 lidar_port:=/dev/ldlidar
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# mrobot_namespace.py is a plain module that lives next to this launch file.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from mrobot_namespace import (  # noqa: E402
    namespaced,
    resolve_namespace,
    robot_namespace_argument,
    tf_remappings,
)


def _setup(context, *args, **kwargs):
    namespace = resolve_namespace(context)
    use_sim_time = LaunchConfiguration("use_sim_time")
    lidar_port = LaunchConfiguration("lidar_port")
    lidar_baudrate = LaunchConfiguration("lidar_baudrate")
    laser_scan_dir = LaunchConfiguration("laser_scan_dir")
    laser_yaw = LaunchConfiguration("laser_yaw")

    xacro_file = os.path.join(get_package_share_directory(
        "irobot_create_description"), "urdf", "create3_ld19.urdf.xacro")
    robot_description = ParameterValue(Command([FindExecutable(
        name="xacro"), " ", xacro_file, " laser_yaw:=", laser_yaw]), value_type=str)

    # The only node that uses TF: the rest do not need the remap.
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": use_sim_time}],
        remappings=tf_remappings(namespace),
    )

    # LD19 driver: publishes LaserScan on `scan_raw` (frame laser_frame, defined in the xacro).
    # LaunchConfiguration yields a str, so baudrate and scan_dir are converted with ParameterValue.
    ldlidar = Node(
        package="ldlidar_stl_ros2",
        executable="ldlidar_stl_ros2_node",
        name="ldlidar_publisher_ld19",
        output="screen",
        parameters=[
            {
                "product_name": "LDLiDAR_LD19",
                "topic_name": "scan_raw",
                "frame_id": "laser_frame",
                "port_name": lidar_port,
                "port_baudrate": ParameterValue(lidar_baudrate, value_type=int),
                "laser_scan_dir": ParameterValue(laser_scan_dir, value_type=bool),
                "enable_angle_crop_func": False,
                "angle_crop_min": 135.0,
                "angle_crop_max": 225.0,
            }
        ],
    )

    # scan_raw (500-504 variable beams) -> scan (fixed num_beams), which is what slam_toolbox requires.
    scan_resampler = Node(
        package="mrobot_bringup",
        executable="scan_resampler.py",
        name="scan_resampler",
        output="screen",
        parameters=[{"input_topic": "scan_raw",
                     "output_topic": "scan", "num_beams": 500}],
    )

    # odom (BEST_EFFORT, from the Create 3) -> odom_reliable (RELIABLE). Only consumed by Nav2.
    odom_relay = Node(
        package="mrobot_bringup",
        executable="odom_relay.py",
        name="odom_relay",
        output="screen",
        parameters=[{"input_topic": "odom", "output_topic": "odom_reliable"}],
    )

    return namespaced(namespace, [robot_state_publisher, ldlidar, scan_resampler, odom_relay])


def generate_launch_description():
    return LaunchDescription(
        [
            robot_namespace_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "lidar_port",
                default_value="/dev/ttyUSB0",
                description="LD19 serial port (a udev symlink is recommended, e.g. /dev/ldlidar).",
            ),
            DeclareLaunchArgument("lidar_baudrate", default_value="230400"),
            DeclareLaunchArgument(
                "laser_scan_dir",
                default_value="true",
                description="LD19 scan direction (true|false). Flip it if the scan turns opposite to the robot.",
            ),
            DeclareLaunchArgument(
                "laser_yaw",
                default_value="0.0",
                description="LD19 rotation relative to the robot front (rad). -1.5707963 was used with the real sensor.",
            ),
            OpaqueFunction(function=_setup),
        ]
    )
