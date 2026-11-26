"""Hardware base: robot_state_publisher (xacro) + LiDAR driver + scan_resampler.

NOTE: the iRobot Create 3 is NOT launched here. It runs its own firmware and is reached over the network
(Wi-Fi or Ethernet over USB). The Raspberry Pi 5 must use the same ROS_DOMAIN_ID and RMW as the Create 3
(configured in its web UI: Application > ROS 2). The Create 3 lives in the /r2 namespace; the nodes of this
launch are put under the same `robot_namespace` and TF is remapped to <ns>/tf and <ns>/tf_static. The
namespace is applied here ONCE (see mrobot_namespace.py): do not wrap this launch in another namespace.

LiDAR: lidar_model:=<name> picks config/lidars/<name>.yaml (driver, port, number of beams, ranges, yaw) and the
URDF model lidar_<name>.urdf.xacro. Default: env LIDAR_MODEL or 'ld19'.

Usage:
    ros2 launch mrobot_bringup hardware_base.launch.py lidar_model:=rplidar_c1
    ros2 launch mrobot_bringup hardware_base.launch.py lidar_model:=ld19 laser_yaw:=-1.5707963
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
from lidar_profile import lidar_model_argument, load_lidar_profile  # noqa: E402
from mrobot_namespace import (  # noqa: E402
    namespaced,
    resolve_namespace,
    robot_namespace_argument,
    tf_remappings,
)


def _setup(context, *args, **kwargs):
    namespace = resolve_namespace(context)
    use_sim_time = LaunchConfiguration("use_sim_time")
    model, profile = load_lidar_profile(context)
    driver = profile["driver"]

    # Empty launch arguments keep the profile value.
    lidar_port = LaunchConfiguration("lidar_port").perform(context).strip()
    laser_yaw = LaunchConfiguration("laser_yaw").perform(context).strip() or str(profile["laser_yaw"])
    driver_params = dict(driver["parameters"])
    if lidar_port:
        driver_params[driver["port_parameter"]] = lidar_port

    xacro_file = os.path.join(get_package_share_directory(
        "irobot_create_description"), "urdf", "create3_lidar.urdf.xacro")
    robot_description = ParameterValue(Command([
        FindExecutable(name="xacro"), " ", xacro_file,
        " lidar_model:=", model, " laser_yaw:=", laser_yaw]), value_type=str)

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

    # LiDAR driver from the profile: publishes LaserScan on `scan_raw` (frame laser_frame, defined in the xacro).
    lidar_driver = Node(
        package=driver["package"],
        executable=driver["executable"],
        name=driver["name"],
        output="screen",
        parameters=[driver_params],
        remappings=list(driver.get("remappings", {}).items()),
    )

    # scan_raw (the number of beams may vary) -> scan (fixed num_beams), which is what slam_toolbox requires.
    scan_resampler = Node(
        package="mrobot_bringup",
        executable="scan_resampler.py",
        name="scan_resampler",
        output="screen",
        parameters=[{"input_topic": "scan_raw",
                     "output_topic": "scan",
                     "num_beams": profile["num_beams"]}],
    )

    # odom (BEST_EFFORT, from the Create 3) -> odom_reliable (RELIABLE). Only consumed by Nav2.
    odom_relay = Node(
        package="mrobot_bringup",
        executable="odom_relay.py",
        name="odom_relay",
        output="screen",
        parameters=[{"input_topic": "odom", "output_topic": "odom_reliable"}],
    )

    return namespaced(namespace, [robot_state_publisher, lidar_driver, scan_resampler, odom_relay])


def generate_launch_description():
    return LaunchDescription(
        [
            robot_namespace_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            lidar_model_argument(),
            DeclareLaunchArgument(
                "lidar_port", default_value="",
                description="LiDAR serial port. Empty = the profile value (/dev/lidar, udev symlink)."),
            DeclareLaunchArgument(
                "laser_yaw", default_value="",
                description="LiDAR frame rotation relative to the robot front (rad). Empty = the profile value."),
            OpaqueFunction(function=_setup),
        ]
    )
