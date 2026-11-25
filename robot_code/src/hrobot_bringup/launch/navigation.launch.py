"""Robot real, navegación: hardware_base (robot_state_publisher + LD19 + relays) + map_server + AMCL + Nav2 + RViz.

El mapa se crea antes con `mapping.launch.py` (teleoperación) y se guarda con scripts/save_map.sh.
Aquí se navega sobre él con AMCL.

AMCL necesita saber dónde está el robot al arrancar. Por defecto (set_initial_pose:=true) lo coloca en
initial_x/y/yaw, que por defecto es 0,0,0 = el origen del mapa, o sea el punto desde el que se mapeó
(el dock): pon el robot ahí antes de lanzar. Si está en otro sitio, pasa initial_x/y/yaw, o
set_initial_pose:=false y usa "2D Pose Estimate" en RViz.

Cada include aplica el namespace por su cuenta: este launch NO lo envuelve en otro.

Uso:
    ros2 launch hrobot_bringup navigation.launch.py map_yaml:=$HOME/MaterialenBuddy/robot_code/maps/mapa1.yaml \\
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
from hrobot_namespace import robot_namespace_argument  # noqa: E402


def generate_launch_description():
    launch_dir = os.path.join(
        get_package_share_directory("hrobot_bringup"), "launch")
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

    # odom_topic "odom_reliable": el Create 3 publica odom BEST_EFFORT y Nav2 lo pide RELIABLE;
    # el odom_relay que arranca hardware_base lo republica en ese topic.
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
        }.items(),
    )

    return LaunchDescription(
        [
            robot_namespace_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "map_yaml", description="Ruta absoluta al .yaml del mapa."),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument(
                "lidar_port",
                default_value="/dev/ttyUSB0",
                description="Puerto serie del LD19; p. ej. /dev/ldlidar.",
            ),
            DeclareLaunchArgument("lidar_baudrate", default_value="230400"),
            DeclareLaunchArgument(
                "laser_scan_dir", default_value="true", description="true|false"),
            DeclareLaunchArgument(
                "laser_yaw", default_value="0.0", description="Giro del LD19 (rad)."),
            DeclareLaunchArgument(
                "set_initial_pose",
                default_value="true",
                description="true = AMCL arranca en initial_x/y/yaw (por defecto el origen del mapa, el dock). "
                "false = fijar la pose con 2D Pose Estimate en RViz.",
            ),
            DeclareLaunchArgument("initial_x", default_value="0.0"),
            DeclareLaunchArgument("initial_y", default_value="0.0"),
            DeclareLaunchArgument("initial_yaw", default_value="0.0"),
            nav,  # primero: valida map_yaml antes de arrancar ningún proceso
            hardware,
        ]
    )
