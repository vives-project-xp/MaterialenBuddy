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

    # TODO 1: ruta al xacro: <share de irobot_create_description>/urdf/create3_ld19.urdf.xacro
    #         y robot_description = ParameterValue(Command([FindExecutable(name="xacro"), " ", xacro_file,
    #         " laser_yaw:=", laser_yaw]), value_type=str)
    xacro_file = ...
    robot_description = ...

    # TODO 2: Node de robot_state_publisher (name="robot_state_publisher", output="screen") con
    #         parameters=[{"robot_description": robot_description, "use_sim_time": use_sim_time}]
    #         y remappings=tf_remappings(namespace).
    robot_state_publisher = ...

    # TODO 3: Node del driver: package="ldlidar_stl_ros2", executable="ldlidar_stl_ros2_node",
    #         name="ldlidar_publisher_ld19", output="screen". Parámetros:
    #           product_name "LDLiDAR_LD19", topic_name "scan_raw", frame_id "laser_frame",
    #           port_name lidar_port,
    #           port_baudrate ParameterValue(lidar_baudrate, value_type=int)   (LaunchConfiguration da str)
    #           laser_scan_dir ParameterValue(laser_scan_dir, value_type=bool)
    #           enable_angle_crop_func False, angle_crop_min 135.0, angle_crop_max 225.0
    ldlidar = ...

    # TODO 4: Node de scan_resampler: package="hrobot_bringup", executable="scan_resampler.py",
    #         name="scan_resampler", output="screen",
    #         parameters=[{"input_topic": "scan_raw", "output_topic": "scan", "num_beams": <tu decisión>}]
    scan_resampler = ...

    # TODO 5 (cuando termines odom_relay.py): añade aquí su Node (executable="odom_relay.py") y
    #         agrégalo a la lista. Hoy el odom_relay solo hace falta para Nav2 (paso 4).

    return namespaced(namespace, [robot_state_publisher, ldlidar, scan_resampler])


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
