"""slam_toolbox (online async, mapeo) + RViz. Sin hardware: solo lo que hace el SLAM.

Lo incluye `mapping.launch.py` (robot real) y, más adelante, la simulación.

Argumentos: robot_namespace (env CREATE3_ROBOT_NAMESPACE o 'r2'; vacío = ninguno), use_sim_time (false),
rviz (true).

Namespace: PushRosNamespace (GroupAction) alrededor de slam_toolbox y rviz2, que son los nodos creados aquí.
TF se remapea a <ns>/tf y <ns>/tf_static y el YAML se reescribe con RewrittenYaml(root_key=<ns>);
con namespace vacío no se empuja ni se reescribe nada.

slam_toolbox en ROS 2 Jazzy es un LifecycleNode: arranca en estado "unconfigured" y hay que
configurarlo y activarlo (como en su propio online_async_launch.py).
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
from hrobot_namespace import (  # noqa: E402
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
    pkg = get_package_share_directory("hrobot_bringup")

    slam_yaml = rewrite_yaml(os.path.join(
        pkg, "config", "slam_params.yaml"), namespace)

    tf_remaps = tf_remappings(namespace)

    # slam_toolbox publica /map y /map_metadata con nombre ABSOLUTO, así que PushRosNamespace
    # no los mueve bajo /r2: hay que remapearlos a mano (solo si hay namespace).
    slam_remaps = list(tf_remaps)
    if namespace:
        slam_remaps += [("/map", f"/{namespace}/map"),
                        ("/map_metadata", f"/{namespace}/map_metadata")]

    # namespace="" porque el namespace lo pone PushRosNamespace (LifecycleNode exige un str).
    slam_node = LifecycleNode(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        namespace="",
        output="screen",
        parameters=[slam_yaml, {"use_sim_time": use_sim_time}],
        remappings=slam_remaps,
    )

    # Paso 1 del ciclo de vida: unconfigured -> inactive.
    configure_slam = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_node),
            transition_id=Transition.TRANSITION_CONFIGURE,
        )
    )

    # Paso 2: cuando termina de configurarse (configuring -> inactive), lo activa (inactive -> active).
    activate_slam = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_node,
            start_state="configuring",
            goal_state="inactive",
            entities=[
                LogInfo(msg="slam_toolbox configurado, activando..."),
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(slam_node),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        )
    )

    # RViz: '/<robot_namespace>' en el .rviz se sustituye por '/<ns>' (o '' sin namespace).
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
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="true|false"),
            OpaqueFunction(function=_setup),
        ]
    )
