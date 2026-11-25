"""Gazebo (Harmonic) + Create 3 / LD19 simulado + slam_toolbox o Nav2 + RViz.

Argumentos: world (room.sdf), headless (false), rviz (true), x / y / yaw (pose de spawn),
nav (false), map_yaml.

nav:=false (por defecto): slam_toolbox para mapear con teleoperación.
nav:=true: navegación autónoma sobre un mapa guardado (map_server + AMCL + Nav2) en vez de slam_toolbox;
requiere map_yaml:=<ruta absoluta al .yaml>. AMCL arranca en la pose de spawn (x/y/yaw), que coincide con
el origen del mapa si éste se creó lanzando la simulación sin mover x/y/yaw.

La simulación corre SIN namespace (/cmd_vel, /scan, /odom, /map, /tf): igual que el robot real con
`robot_namespace:=''`. Para mover el robot con el teclado:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
Todos los nodos ROS usan use_sim_time:=true (reloj de Gazebo vía /clock).

Cómo se mueve el robot simulado: el URDF oficial carga el plugin gz_ros2_control, que ejecuta un
controller_manager. Hay que arrancar dos controladores (joint_state_broadcaster y diffdrive_controller);
el segundo publica /odom y el TF odom -> base_link. Por eso aquí no hay puente de cmd_vel/odom/tf.
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
    sim_share = get_package_share_directory("hrobot_simulation")
    bringup_share = get_package_share_directory("hrobot_bringup")
    description_share = get_package_share_directory(
        "irobot_create_description")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    world = LaunchConfiguration("world")
    headless = LaunchConfiguration("headless")

    # Para que Gazebo resuelva las mallas package://irobot_create_description/meshes/...
    # Gazebo busca la carpeta irobot_create_description dentro de esa ruta: el directorio PADRE.
    gz_resource_path = SetEnvironmentVariable(
        "GZ_SIM_RESOURCE_PATH",
        [os.path.dirname(description_share), ":",
         os.environ.get("GZ_SIM_RESOURCE_PATH", "")],
    )

    # `gazebo:=ignition` activa los plugins de Gazebo Harmonic: ros2_control, sensores y el LiDAR simulado del LD19.
    robot_description = ParameterValue(
        Command([FindExecutable(name="xacro"), " ", os.path.join(description_share,
                "urdf", "create3_ld19.urdf.xacro"), " gazebo:=ignition laser_yaw:=0"]),
        value_type=str,
    )

    # Gazebo: servidor + GUI (-r: arranca ejecutando). headless: solo servidor (-s), sin GUI.
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

    # Mete el robot en Gazebo leyendo el topic robot_description (z=0.01 evita que nazca incrustado en el suelo).
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

    # Puente ROS <-> Gazebo (solo /clock y /scan, ver config/gz_bridge.yaml)
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

    # Controladores de ros2_control. El controller_manager no existe hasta que el robot aparece en Gazebo;
    # el timeout de 60 s hace que el spawner espere. diffdrive_controller arranca DESPUÉS del broadcaster.
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

    # Conversor Twist (teleop, Nav2) -> TwistStamped (diff_drive_controller de Jazzy).
    cmd_vel_stamper = Node(
        package="hrobot_simulation",
        executable="cmd_vel_stamper.py",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    # Los dos modos de trabajo, ambos sin namespace y con tiempo de simulación:
    #   * slam: mapear con teleop (nav:=false).
    #   * nav_launch: navegar sobre un mapa guardado (nav:=true). AMCL arranca en la pose de spawn.
    #     No hace falta odom_topic: en simulación Nav2 lee "odom" (valor por defecto).
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
                description="Ruta al mundo de Gazebo (.sdf).",
            ),
            DeclareLaunchArgument(
                "headless", default_value="false", description="true = Gazebo sin GUI."),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument(
                "nav", default_value="false", description="true = AMCL + Nav2 en vez de slam_toolbox."
            ),
            DeclareLaunchArgument(
                "map_yaml", default_value="", description="Con nav:=true: ruta absoluta al .yaml del mapa."
            ),
            DeclareLaunchArgument("x", default_value="0.0"),
            DeclareLaunchArgument("y", default_value="0.0"),
            DeclareLaunchArgument("yaw", default_value="0.0"),
            gz_resource_path,
            slam,  # primero: nav.launch.py valida map_yaml antes de arrancar procesos
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
