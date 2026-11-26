"""Display the create3_lidar model in RViz (no real robot or simulation).

Usage:
    ros2 launch irobot_create_description display.launch.py
    ros2 launch irobot_create_description display.launch.py lidar_model:=rplidar_c1 laser_yaw:=3.14159265
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('irobot_create_description')

    xacro_file = os.path.join(pkg, 'urdf', 'create3_lidar.urdf.xacro')

    # RViz configuration: created from RViz and saved to rviz/model.rviz.
    rviz_file = os.path.join(pkg, 'rviz', 'model.rviz')

    declare_lidar_model = DeclareLaunchArgument(
        'lidar_model', default_value=EnvironmentVariable('LIDAR_MODEL', default_value='ld19'),
        description='LiDAR URDF model: urdf/sensors/lidar_<model>.urdf.xacro')

    # Launch argument to rotate the LiDAR frame (rad).
    laser_yaw = LaunchConfiguration('laser_yaw')
    declare_laser_yaw = DeclareLaunchArgument(
        'laser_yaw', default_value='0.0',
        description='LiDAR frame rotation relative to the robot front (rad)')

    # Process the xacro (xacro args are passed as `name:=value`). ParameterValue(..., value_type=str)
    # makes robot_state_publisher receive the result as a string and not try to interpret it.
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' lidar_model:=', LaunchConfiguration('lidar_model'),
                 ' laser_yaw:=', laser_yaw]), value_type=str)

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
        declare_lidar_model,
        declare_laser_yaw,
        robot_state_publisher,
        joint_state_publisher,
        rviz,
    ])
