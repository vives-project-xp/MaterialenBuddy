"""Navegación autónoma con Nav2 + AMCL + RViz. Sin hardware.

Lo incluye `navigation.launch.py` (robot real) y, más adelante, la simulación.

Localización: map_server (mapa guardado) + AMCL, que publica map -> odom. No corre slam_toolbox.

Argumentos: robot_namespace (env CREATE3_ROBOT_NAMESPACE o 'r2'; vacío = ninguno), use_sim_time (false),
map_yaml (ruta absoluta al .yaml del mapa; obligatorio), rviz (true), params_file (config/nav2_params.yaml),
autostart (true), odom_topic ('odom'; 'odom_reliable' en el robot real, ver odom_relay.py),
set_initial_pose (false), initial_x / initial_y / initial_yaw (0.0).

Namespace: igual que slam.launch.py (PushRosNamespace, TF relativo, RewrittenYaml).

Cómo está montado Nav2: son varios nodos con ciclo de vida. Cada grupo lo arranca un lifecycle_manager
que lee la lista `node_names` del YAML y los configura y activa en orden:
  * localización: map_server + amcl            (lifecycle_manager_localization)
  * navegación:   controller_server, smoother_server, planner_server, behavior_server, bt_navigator
                                               (lifecycle_manager_navigation)
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from hrobot_namespace import (  # noqa: E402
    namespaced,
    resolve_namespace,
    rewrite_yaml,
    robot_namespace_argument,
    substitute_namespace_markers,
    tf_remappings,
)


def _truthy(context, name):
    """Lee un argumento de launch y lo interpreta como booleano."""
    return LaunchConfiguration(name).perform(context).strip().lower() in ("true", "1", "yes")


def _setup(context, *args, **kwargs):
    namespace = resolve_namespace(context)
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    pkg = get_package_share_directory("hrobot_bringup")

    # El mapa es obligatorio. Este launch se incluye PRIMERO, así que el error salta antes de
    # arrancar ningún proceso.
    map_yaml_arg = LaunchConfiguration("map_yaml").perform(context).strip()
    map_yaml = os.path.abspath(os.path.expanduser(map_yaml_arg)) if map_yaml_arg else ""
    if not map_yaml or not os.path.isfile(map_yaml):
        raise RuntimeError(
            f"map_yaml:='{map_yaml_arg}' no existe o está vacío. Pasa la ruta absoluta al .yaml del mapa, "
            "p. ej. map_yaml:=$HOME/MaterialenBuddy/robot_code/maps/mapa1.yaml "
            "(se genera con scripts/save_map.sh)."
        )

    # El YAML pasa por DOS transformaciones y el ORDEN importa: primero los marcadores
    # ('/<robot_namespace>/scan' -> '/r2/scan') y después rewrite_yaml (envuelve los nodos bajo r2).
    params_file = rewrite_yaml(
        substitute_namespace_markers(LaunchConfiguration("params_file"), namespace),
        namespace,
    )

    tf_remaps = tf_remappings(namespace)
    odom_topic = LaunchConfiguration("odom_topic")

    # Parámetros comunes a todos los nodos de Nav2.
    common = [params_file, {"use_sim_time": use_sim_time}]

    def nav2_node(package, executable, name=None, extra=None):
        # `extra` es un dict de parámetros que PISA los del YAML (p. ej. yaml_filename del map_server).
        return Node(
            package=package,
            executable=executable,
            name=name or executable,
            output="screen",
            parameters=common + ([extra] if extra else []),
            remappings=tf_remaps,
        )

    # Pose inicial de AMCL (solo se usa si set_initial_pose es true).
    initial_pose = {
        "set_initial_pose": _truthy(context, "set_initial_pose"),
        "initial_pose": {
            "x": float(LaunchConfiguration("initial_x").perform(context)),
            "y": float(LaunchConfiguration("initial_y").perform(context)),
            "z": 0.0,
            "yaw": float(LaunchConfiguration("initial_yaw").perform(context)),
        },
    }

    # Localización: map_server + amcl. El name del lifecycle_manager debe coincidir con la clave del YAML.
    localization_nodes = [
        nav2_node("nav2_map_server", "map_server", extra={"yaml_filename": map_yaml}),
        nav2_node("nav2_amcl", "amcl", extra=initial_pose),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_localization",
            output="screen",
            parameters=common + [{"autostart": autostart}],
        ),
    ]

    # Navegación: controller y bt_navigator leen la odometría (odom_topic).
    navigation_nodes = [
        nav2_node("nav2_controller", "controller_server", extra={"odom_topic": odom_topic}),
        nav2_node("nav2_smoother", "smoother_server"),
        nav2_node("nav2_planner", "planner_server"),
        nav2_node("nav2_behaviors", "behavior_server"),
        nav2_node("nav2_bt_navigator", "bt_navigator", extra={"odom_topic": odom_topic}),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_navigation",
            output="screen",
            parameters=common + [{"autostart": autostart}],
        ),
    ]

    # RViz: '/<robot_namespace>' en el .rviz se sustituye por '/<ns>' (o '' sin namespace).
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", substitute_namespace_markers(os.path.join(pkg, "rviz", "navigation.rviz"), namespace)],
        parameters=[{"use_sim_time": use_sim_time}],
        remappings=tf_remaps,
        output="screen",
        condition=IfCondition(LaunchConfiguration("rviz")),
    )

    return namespaced(namespace, [*localization_nodes, *navigation_nodes, rviz])


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory("hrobot_bringup"), "config", "nav2_params.yaml"
    )
    return LaunchDescription(
        [
            robot_namespace_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "map_yaml",
                default_value="",
                description="Ruta absoluta al .yaml del mapa (map_server). Obligatorio.",
            ),
            DeclareLaunchArgument("rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument("params_file", default_value=default_params),
            DeclareLaunchArgument("autostart", default_value="true"),
            DeclareLaunchArgument(
                "odom_topic",
                default_value="odom",
                description="Topic de odometría que lee Nav2. 'odom_reliable' con el robot real.",
            ),
            DeclareLaunchArgument(
                "set_initial_pose",
                default_value="false",
                description="true = AMCL arranca en initial_x/y/yaw; false = usar 2D Pose Estimate en RViz.",
            ),
            DeclareLaunchArgument("initial_x", default_value="0.0"),
            DeclareLaunchArgument("initial_y", default_value="0.0"),
            DeclareLaunchArgument("initial_yaw", default_value="0.0"),
            OpaqueFunction(function=_setup),
        ]
    )
