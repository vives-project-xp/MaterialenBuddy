"""slam_toolbox (online async, mapping) + RViz. No hardware: only what the SLAM does.

Included by `mapping.launch.py` (real robot) and by the simulation.

Arguments: robot_namespace (env CREATE3_ROBOT_NAMESPACE or 'r2'; empty = none), use_sim_time (false),
lidar_model (env LIDAR_MODEL or 'ld19'),
rviz (true), posegraph ('' = start an empty map; otherwise the path WITHOUT extension of a saved
.posegraph/.data pair: slam_toolbox loads it and keeps extending it), initial_x / initial_y / initial_yaw
(robot pose in that map when it is loaded; 0 0 0 = the map origin).

Namespace: PushRosNamespace (GroupAction) around slam_toolbox and rviz2, which are the nodes created here.
TF is remapped to <ns>/tf and <ns>/tf_static and the YAML is rewritten with RewrittenYaml(root_key=<ns>);
with an empty namespace nothing is pushed or rewritten.

slam_toolbox in ROS 2 Jazzy is a LifecycleNode: it starts in the "unconfigured" state and has to be
configured and activated (as in its own online_async_launch.py).
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition

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


def _setup(context, *args, **kwargs):
    namespace = resolve_namespace(context)
    use_sim_time = LaunchConfiguration("use_sim_time")
    pkg = get_package_share_directory("mrobot_bringup")

    slam_yaml = rewrite_yaml(os.path.join(
        pkg, "config", "slam_params.yaml"), namespace)

    tf_remaps = tf_remappings(namespace)

    # The LiDAR ranges come from the profile and override slam_params.yaml.
    _, profile = load_lidar_profile(context)
    lidar_ranges = {"min_laser_range": float(profile["min_range"]),
                    "max_laser_range": float(profile["max_range"])}

    # slam_toolbox publishes /map and /map_metadata with an ABSOLUTE name, so PushRosNamespace
    # does not move them under /r2: they have to be remapped by hand (only when there is a namespace).
    slam_remaps = list(tf_remaps)
    if namespace:
        slam_remaps += [("/map", f"/{namespace}/map"),
                        ("/map_metadata", f"/{namespace}/map_metadata")]

    # Resume a saved map: slam_toolbox deserializes the pose graph when it configures and keeps mapping on it.
    extra = {}
    posegraph = LaunchConfiguration("posegraph").perform(context).strip()
    if posegraph:
        posegraph = os.path.abspath(os.path.expanduser(posegraph))
        for ext in ("posegraph", "data"):
            if not os.path.isfile(f"{posegraph}.{ext}"):
                raise RuntimeError(f"{posegraph}.{ext} does not exist (generate it with scripts/save_map.sh).")
        extra = {
            "map_file_name": posegraph,
            "map_start_pose": [float(LaunchConfiguration(k).perform(context))
                               for k in ("initial_x", "initial_y", "initial_yaw")],
        }

    # namespace="" because the namespace comes from PushRosNamespace (LifecycleNode requires a str).
    slam_node = LifecycleNode(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        namespace="",
        output="screen",
        parameters=[slam_yaml, {"use_sim_time": use_sim_time, **lidar_ranges}, extra],
        remappings=slam_remaps,
    )

    # Lifecycle step 1: unconfigured -> inactive.
    configure_slam = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_node),
            transition_id=Transition.TRANSITION_CONFIGURE,
        )
    )

    # Step 2: once it finishes configuring (configuring -> inactive), activate it (inactive -> active).
    activate_slam = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_node,
            start_state="configuring",
            goal_state="inactive",
            entities=[
                LogInfo(msg="slam_toolbox configured, activating..."),
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(slam_node),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        )
    )

    # RViz: '/<robot_namespace>' in the .rviz is replaced by '/<ns>' (or '' without a namespace).
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=[
            "-d", substitute_namespace_markers(os.path.join(pkg, "rviz", "mapping.rviz"), namespace)],
        parameters=[{"use_sim_time": use_sim_time}],
        remappings=tf_remaps,
        output="screen",
        condition=IfCondition(LaunchConfiguration("rviz")),
    )

    return namespaced(namespace, [slam_node, configure_slam, activate_slam, rviz])


def generate_launch_description():
    return LaunchDescription(
        [
            robot_namespace_argument(),
            lidar_model_argument(),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            DeclareLaunchArgument("posegraph", default_value=""),
            DeclareLaunchArgument("initial_x", default_value="0.0"),
            DeclareLaunchArgument("initial_y", default_value="0.0"),
            DeclareLaunchArgument("initial_yaw", default_value="0.0"),
            OpaqueFunction(function=_setup),
        ]
    )
