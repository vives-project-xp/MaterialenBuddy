"""Visualiza el modelo create3_ld19 en RViz (sin robot real ni simulación).

Uso:
    ros2 launch irobot_create_description display.launch.py
    ros2 launch irobot_create_description display.launch.py laser_yaw:=-1.5707963
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('irobot_create_description')

    xacro_file = os.path.join(pkg, 'urdf', 'create3_ld19.urdf.xacro')

    # Configuración de RViz: se crea desde RViz y se guarda en rviz/model.rviz.
    rviz_file = os.path.join(pkg, 'rviz', 'model.rviz')

    # Argumento de launch para girar el LD19 (rad).
    laser_yaw = LaunchConfiguration('laser_yaw')
    declare_laser_yaw = DeclareLaunchArgument(
        'laser_yaw', default_value='0.0',
        description='Giro del LD19 respecto al frente del robot (rad)')

    # Procesa el xacro (los args del xacro se pasan como `nombre:=valor`). ParameterValue(..., value_type=str)
    # hace que robot_state_publisher reciba el resultado como cadena y no intente interpretarlo.
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' laser_yaw:=', laser_yaw]), value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    # Sin él, las ruedas (articulaciones continuas) no tienen TF y RViz las marca en rojo.
    joint_state_publisher = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui'
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_file]
    )

    return LaunchDescription([
        declare_laser_yaw,
        robot_state_publisher,
        joint_state_publisher,
        rviz,
    ])
