"""Base de hardware: robot_state_publisher (xacro) + driver del LiDAR LD19 + scan_resampler.

NOTA: el Create 3 NO se lanza aquí. Corre su propio firmware y se alcanza por red (Wi-Fi o Ethernet sobre
USB). La Raspberry Pi 5 debe usar el mismo ROS_DOMAIN_ID y RMW que el Create 3 (se configura en su web:
Application > ROS 2). El Create 3 vive en el namespace /r2; los nodos de este launch se ponen bajo el mismo
`robot_namespace` y TF se remapea a <ns>/tf y <ns>/tf_static. El namespace se aplica aquí UNA vez (ver
hrobot_namespace.py): no envuelvas este launch en otro namespace.

Driver del LD19: `ldlidar_stl_ros2` de LDRobot (ejecutable `ldlidar_stl_ros2_node`). Se compila desde el
código fuente en el workspace; no está disponible por rosdep.

Uso:
    ros2 launch hrobot_bringup hardware_base.launch.py
    ros2 launch hrobot_bringup hardware_base.launch.py laser_yaw:=-1.5707963 lidar_port:=/dev/ldlidar
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# hrobot_namespace.py es un módulo normal que vive junto a este launch.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from hrobot_namespace import (  # noqa: E402
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

    # Único nodo que usa TF: el resto no necesita remapearlo.
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": use_sim_time}],
        remappings=tf_remappings(namespace),
    )

    # Driver del LD19: publica LaserScan en `scan_raw` (frame laser_frame, definido en el xacro).
    # LaunchConfiguration da str, por eso baudrate y scan_dir se convierten con ParameterValue.
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

    # scan_raw (500-504 rayos variables) -> scan (num_beams fijo), que es lo que exige slam_toolbox.
    scan_resampler = Node(
        package="hrobot_bringup",
        executable="scan_resampler.py",
        name="scan_resampler",
        output="screen",
        parameters=[{"input_topic": "scan_raw",
                     "output_topic": "scan", "num_beams": 500}],
    )

    # odom (BEST_EFFORT, del Create 3) -> odom_reliable (RELIABLE). Solo lo consume Nav2 (paso 4).
    odom_relay = Node(
        package="hrobot_bringup",
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
                description="Puerto serie del LD19 (conviene un enlace udev, p. ej. /dev/ldlidar).",
            ),
            DeclareLaunchArgument("lidar_baudrate", default_value="230400"),
            DeclareLaunchArgument(
                "laser_scan_dir",
                default_value="true",
                description="Sentido de giro del LD19 (true|false). Cámbialo si el scan gira al revés que el robot.",
            ),
            DeclareLaunchArgument(
                "laser_yaw",
                default_value="0.0",
                description="Giro del LD19 respecto al frente del robot (rad). Con el sensor real se usó -1.5707963.",
            ),
            OpaqueFunction(function=_setup),
        ]
    )
