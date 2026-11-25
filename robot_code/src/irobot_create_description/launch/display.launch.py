"""Display the create3_ld19 model in RViz (no real robot or simulation).

Usage:
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

    # RViz configuration: created from RViz and saved to rviz/model.rviz.
    rviz_file = os.path.join(pkg, 'rviz', 'model.rviz')

    # Launch argument to rotate the LD19 (rad).
    laser_yaw = LaunchConfiguration('laser_yaw')
    declare_laser_yaw = DeclareLaunchArgument(
        'laser_yaw', default_value='0.0',
        description='LD19 rotation relative to the robot front (rad)')

    # Process the xacro (xacro args are passed as `name:=value`). ParameterValue(..., value_type=str)
    # makes robot_state_publisher receive the result as a string and not try to interpret it.
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' laser_yaw:=', laser_yaw]), value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    # Without it, the wheels (continuous joints) have no TF and RViz marks them in red.
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
