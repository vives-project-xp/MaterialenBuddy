"""Gazebo (Harmonic) + simulated Create 3 / LD19 + slam_toolbox or Nav2 + RViz.

Arguments: world (room.sdf), headless (false), rviz (true), x / y / yaw (spawn pose),
nav (false), map_yaml.

nav:=false (default): slam_toolbox to map with teleoperation.
nav:=true: autonomous navigation on a saved map (map_server + AMCL + Nav2) instead of slam_toolbox;
requires map_yaml:=<absolute path to the .yaml>. AMCL starts at the spawn pose (x/y/yaw), which matches
the map origin if the map was created by launching the simulation without moving x/y/yaw.

The simulation runs WITHOUT a namespace (/cmd_vel, /scan, /odom, /map, /tf): same as the real robot with
`robot_namespace:=''`. To move the robot with the keyboard:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
All ROS nodes use use_sim_time:=true (Gazebo clock via /clock).

How the simulated robot moves: the official URDF loads the gz_ros2_control plugin, which runs a
controller_manager. Two controllers have to be started (joint_state_broadcaster and diffdrive_controller);
the second one publishes /odom and the odom -> base_link TF. That is why there is no cmd_vel/odom/tf bridge here.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    sim_share = get_package_share_directory("mrobot_simulation")
    bringup_share = get_package_share_directory("mrobot_bringup")
    description_share = get_package_share_directory(
        "irobot_create_description")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    world = LaunchConfiguration("world")
    headless = LaunchConfiguration("headless")

    # So Gazebo can resolve the package://irobot_create_description/meshes/... meshes.
    # Gazebo looks for the irobot_create_description folder inside that path: the PARENT directory.
    gz_resource_path = SetEnvironmentVariable(
        "GZ_SIM_RESOURCE_PATH",
        [os.path.dirname(description_share), ":",
         os.environ.get("GZ_SIM_RESOURCE_PATH", "")],
    )

    # `gazebo:=ignition` enables the Gazebo Harmonic plugins: ros2_control, sensors and the simulated LD19 LiDAR.
    robot_description = ParameterValue(
        Command([FindExecutable(name="xacro"), " ", os.path.join(description_share,
                "urdf", "create3_ld19.urdf.xacro"), " gazebo:=ignition laser_yaw:=0"]),
        value_type=str,
    )

    # Gazebo: server + GUI (-r: start running). headless: server only (-s), no GUI.
    gz_sim_launch = os.path.join(
        ros_gz_sim_share, "launch", "gz_sim.launch.py")
    gz_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={"gz_args": ["-r ", world]}.items(),
        condition=UnlessCondition(headless),
    )
    gz_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={"gz_args": [
            "-r -s --headless-rendering ", world]}.items(),
        condition=IfCondition(headless),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {"robot_description": robot_description, "use_sim_time": True}],
    )

    # Spawns the robot in Gazebo from the robot_description topic (z=0.01 keeps it from spawning embedded in the floor).
    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            "create3",
            "-x",
            LaunchConfiguration("x"),
            "-y",
            LaunchConfiguration("y"),
            "-z",
            "0.01",
            "-Y",
            LaunchConfiguration("yaw"),
        ],
    )

    # ROS <-> Gazebo bridge (only /clock and /scan, see config/gz_bridge.yaml)
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        parameters=[
            {
                "config_file": os.path.join(sim_share, "config", "gz_bridge.yaml"),
                "use_sim_time": True,
            }
        ],
    )

    # ros2_control controllers. The controller_manager does not exist until the robot appears in Gazebo;
    # the 60 s timeout makes the spawner wait. diffdrive_controller starts AFTER the broadcaster.
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c",
                   "controller_manager", "--controller-manager-timeout", "60"],
        output="screen",
    )
    diffdrive_spawner_after_broadcaster = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[
                Node(
                    package="controller_manager",
                    executable="spawner",
                    arguments=["diffdrive_controller", "-c",
                               "controller_manager", "--controller-manager-timeout", "60"],
                    output="screen",
                )
            ],
        )
    )

    # Twist (teleop, Nav2) -> TwistStamped converter (Jazzy diff_drive_controller).
    cmd_vel_stamper = Node(
        package="mrobot_simulation",
        executable="cmd_vel_stamper.py",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    # The two working modes, both without a namespace and with simulation time:
    #   * slam: map with teleop (nav:=false).
    #   * nav_launch: navigate on a saved map (nav:=true). AMCL starts at the spawn pose.
    #     odom_topic is not needed: in simulation Nav2 reads "odom" (the default value).
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            bringup_share, "launch", "slam.launch.py")),
        launch_arguments={
            "robot_namespace": "",
            "use_sim_time": "true",
            "rviz": LaunchConfiguration("rviz"),
        }.items(),
        condition=UnlessCondition(LaunchConfiguration("nav")),
    )
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            bringup_share, "launch", "nav.launch.py")),
        launch_arguments={
            "robot_namespace": "",
            "use_sim_time": "true",
            "map_yaml": LaunchConfiguration("map_yaml"),
            "rviz": LaunchConfiguration("rviz"),
            "set_initial_pose": "true",
            "initial_x": LaunchConfiguration("x"),
            "initial_y": LaunchConfiguration("y"),
            "initial_yaw": LaunchConfiguration("yaw"),
        }.items(),
        condition=IfCondition(LaunchConfiguration("nav")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [sim_share, "worlds", "room.sdf"]),
                description="Path to the Gazebo world (.sdf).",
            ),
            DeclareLaunchArgument(
                "headless", default_value="false", description="true = Gazebo without GUI."),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument(
                "nav", default_value="false", description="true = AMCL + Nav2 instead of slam_toolbox."
            ),
            DeclareLaunchArgument(
                "map_yaml", default_value="", description="With nav:=true: absolute path to the map .yaml."
            ),
            DeclareLaunchArgument("x", default_value="0.0"),
            DeclareLaunchArgument("y", default_value="0.0"),
            DeclareLaunchArgument("yaw", default_value="0.0"),
            gz_resource_path,
            slam,  # first: nav.launch.py validates map_yaml before any process starts
            nav_launch,
            gz_gui,
            gz_headless,
            robot_state_publisher,
            spawn,
            bridge,
            joint_state_broadcaster_spawner,
            diffdrive_spawner_after_broadcaster,
            cmd_vel_stamper,
        ]
    )
