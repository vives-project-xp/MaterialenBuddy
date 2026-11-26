"""Autonomous navigation with Nav2 + AMCL + RViz. No hardware.

Included by `navigation.launch.py` (real robot) and by the simulation.

Localization, two modes (live_mapping):
  * live_mapping:=true (default): slam_toolbox loads the saved pose graph (<map>.posegraph/.data, next to map_yaml)
    and KEEPS MAPPING while navigating: it publishes /map and map -> odom, so new objects update the global
    costmap. map_server and AMCL do not run.
  * live_mapping:=false: map_server (saved map, static) + AMCL, which publishes map -> odom.

Arguments: robot_namespace (env CREATE3_ROBOT_NAMESPACE or 'r2'; empty = none), use_sim_time (false),
map_yaml (absolute path to the map .yaml; required), rviz (true), params_file (config/nav2_params.yaml),
autostart (true), odom_topic ('odom'; 'odom_reliable' on the real robot, see odom_relay.py),
live_mapping (true), lidar_model (env LIDAR_MODEL or 'ld19'), set_initial_pose (false), initial_x / initial_y / initial_yaw (0.0).

Namespace: same as slam.launch.py (PushRosNamespace, relative TF, RewrittenYaml).

How Nav2 is put together: it is several lifecycle nodes. Each group is started by a lifecycle_manager
that reads the `node_names` list from the YAML and configures and activates them in order:
  * localization: map_server + amcl            (lifecycle_manager_localization)
  * navigation:   controller_server, smoother_server, planner_server, behavior_server, bt_navigator
                                               (lifecycle_manager_navigation)
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from lidar_profile import lidar_model_argument, load_lidar_profile  # noqa: E402
from mrobot_namespace import (  # noqa: E402
    namespaced,
    resolve_namespace,
    rewrite_yaml,
    robot_namespace_argument,
    substitute_namespace_markers,
    tf_remappings,
)


def _truthy(context, name):
    """Read a launch argument and interpret it as a boolean."""
    return LaunchConfiguration(name).perform(context).strip().lower() in ("true", "1", "yes")


def _setup(context, *args, **kwargs):
    namespace = resolve_namespace(context)
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    pkg = get_package_share_directory("mrobot_bringup")

    # The map is required. This launch is included FIRST, so the error is raised before
    # any process is started.
    map_yaml_arg = LaunchConfiguration("map_yaml").perform(context).strip()
    map_yaml = os.path.abspath(os.path.expanduser(map_yaml_arg)) if map_yaml_arg else ""
    if not map_yaml or not os.path.isfile(map_yaml):
        raise RuntimeError(
            f"map_yaml:='{map_yaml_arg}' does not exist or is empty. Pass the absolute path to the map .yaml, "
            "e.g. map_yaml:=$HOME/MaterialenBuddy/robot_code/maps/map1.yaml "
            "(it is generated with scripts/save_map.sh)."
        )

    # The YAML goes through TWO transformations and the ORDER matters: first the markers
    # ('/<robot_namespace>/scan' -> '/r2/scan') and then rewrite_yaml (wraps the nodes under r2).
    params_file = rewrite_yaml(
        substitute_namespace_markers(LaunchConfiguration("params_file"), namespace),
        namespace,
    )

    tf_remaps = tf_remappings(namespace)
    odom_topic = LaunchConfiguration("odom_topic")

    # Parameters shared by all the Nav2 nodes.
    common = [params_file, {"use_sim_time": use_sim_time}]

    def nav2_node(package, executable, name=None, extra=None):
        # `extra` is a dict of parameters that OVERRIDES the YAML ones (e.g. the map_server yaml_filename).
        return Node(
            package=package,
            executable=executable,
            name=name or executable,
            output="screen",
            parameters=common + ([extra] if extra else []),
            remappings=tf_remaps,
        )

    # AMCL initial pose (only used if set_initial_pose is true).
    initial_pose = {
        "set_initial_pose": _truthy(context, "set_initial_pose"),
        "initial_pose": {
            "x": float(LaunchConfiguration("initial_x").perform(context)),
            "y": float(LaunchConfiguration("initial_y").perform(context)),
            "z": 0.0,
            "yaw": float(LaunchConfiguration("initial_yaw").perform(context)),
        },
    }

    # AMCL uses the LiDAR ranges of the profile (they override nav2_params.yaml).
    _, profile = load_lidar_profile(context)
    amcl_extra = {**initial_pose,
                  "laser_min_range": float(profile["min_range"]),
                  "laser_max_range": float(profile["max_range"])}

    live_mapping = _truthy(context, "live_mapping")
    if live_mapping:
        base = os.path.splitext(map_yaml)[0]
        # slam_toolbox (mapping mode) over the saved pose graph. It applies the namespace on its own.
        # GroupAction (scoped): without it the include's rviz:=false leaks and RViz (below) would not open.
        localization_nodes = [
            GroupAction([IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "slam.launch.py")),
                launch_arguments={
                    "robot_namespace": namespace,
                    "use_sim_time": use_sim_time,
                    "rviz": "false",
                    "lidar_model": LaunchConfiguration("lidar_model"),
                    "posegraph": base,
                    "initial_x": LaunchConfiguration("initial_x"),
                    "initial_y": LaunchConfiguration("initial_y"),
                    "initial_yaw": LaunchConfiguration("initial_yaw"),
                }.items(),
            )])
        ]
    else:
        # Localization: map_server + amcl. The lifecycle_manager name must match the YAML key.
        localization_nodes = [
            nav2_node("nav2_map_server", "map_server", extra={"yaml_filename": map_yaml}),
            nav2_node("nav2_amcl", "amcl", extra=amcl_extra),
            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="lifecycle_manager_localization",
                output="screen",
                parameters=common + [{"autostart": autostart}],
            ),
        ]

    # Navigation: controller and bt_navigator read the odometry (odom_topic).
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

    # RViz: '/<robot_namespace>' in the .rviz is replaced by '/<ns>' (or '' without a namespace).
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

    # The include (slam) applies the namespace itself: it goes outside the group.
    includes = [x for x in localization_nodes if isinstance(x, GroupAction)]
    plain = [x for x in localization_nodes if not isinstance(x, GroupAction)]
    return includes + namespaced(namespace, [*plain, *navigation_nodes, rviz])


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory("mrobot_bringup"), "config", "nav2_params.yaml"
    )
    return LaunchDescription(
        [
            robot_namespace_argument(),
            lidar_model_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "map_yaml",
                default_value="",
                description="Absolute path to the map .yaml (map_server). Required.",
            ),
            DeclareLaunchArgument("rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument("params_file", default_value=default_params),
            DeclareLaunchArgument("autostart", default_value="true"),
            DeclareLaunchArgument(
                "live_mapping",
                default_value="true",
                description="true = slam_toolbox keeps mapping while navigating (needs <map>.posegraph/.data); "
                "false = static map_server + AMCL.",
            ),
            DeclareLaunchArgument(
                "odom_topic",
                default_value="odom",
                description="Odometry topic read by Nav2. 'odom_reliable' with the real robot.",
            ),
            DeclareLaunchArgument(
                "set_initial_pose",
                default_value="false",
                description="true = AMCL starts at initial_x/y/yaw; false = use 2D Pose Estimate in RViz.",
            ),
            DeclareLaunchArgument("initial_x", default_value="0.0"),
            DeclareLaunchArgument("initial_y", default_value="0.0"),
            DeclareLaunchArgument("initial_yaw", default_value="0.0"),
            OpaqueFunction(function=_setup),
        ]
    )
