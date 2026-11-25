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

    # TODO 1: ruta al xacro del robot: <pkg>/urdf/create3_ld19.urdf.xacro
    xacro_file = os.path.join(pkg, 'urdf', 'create3_ld19.urdf.xacro')

    # TODO 2: ruta al archivo RViz: <pkg>/rviz/model.rviz (lo creas tú desde RViz y lo guardas ahí)
    rviz_file = os.path.join(pkg, 'rviz', 'model.rviz')

    # Argumento de launch para girar el LD19 (rad). Ya declarado como ejemplo.
    laser_yaw = LaunchConfiguration('laser_yaw')
    declare_laser_yaw = DeclareLaunchArgument(
        'laser_yaw', default_value='0.0',
        description='Giro del LD19 respecto al frente del robot (rad)')

    # TODO 3: procesar el xacro con Command(['xacro ', xacro_file, ' laser_yaw:=', laser_yaw, ...]).
    #   - Los args del xacro se pasan como `nombre:=valor`.
    #   - Envuelve el resultado en ParameterValue(..., value_type=str) para que
    #     robot_state_publisher lo reciba como cadena y no intente interpretarlo.
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' laser_yaw:=', laser_yaw]), value_type=str)

    # TODO 4: Node de robot_state_publisher (package='robot_state_publisher',
    #   executable='robot_state_publisher') con parameters=[{'robot_description': robot_description}].
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    # TODO 5: Node de joint_state_publisher_gui (package='joint_state_publisher_gui',
    #   executable='joint_state_publisher_gui'). Sin él, las ruedas no tienen TF y RViz las marca en rojo.
    joint_state_publisher = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui'
    )

    # TODO 6: Node de rviz2 (package='rviz2', executable='rviz2') con arguments=['-d', rviz_file].
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
