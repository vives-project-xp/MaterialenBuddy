"""Helpers shared by the mrobot_bringup launch files (robot namespace handling).

This is not a launch file: it is a plain Python module. The launch files add their own folder to sys.path and import it.

Namespace design (it is applied ONCE, to avoid /r2/r2/...):
  * Every launch file declares `robot_namespace` and applies the namespace itself, only to the nodes it
    creates directly (GroupAction + PushRosNamespace, see `namespaced`).
  * Empty namespace = nothing is applied (simulation, no namespace).
  * The real Create 3 lives in /r2 (it publishes /r2/odom, /r2/tf, /r2/tf_static and listens on /r2/cmd_vel).

It also includes rewrite_yaml() and substitute_namespace_markers() for YAML and .rviz files with a namespace.
"""

import os
import re

from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import PushRosNamespace

ENV_VAR = "CREATE3_ROBOT_NAMESPACE"
FALLBACK_NAMESPACE = "r2"
_NAMESPACE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(/[A-Za-z][A-Za-z0-9_]*)*$")


def default_robot_namespace():
    """Environment variable CREATE3_ROBOT_NAMESPACE if defined (even empty = no namespace); otherwise 'r2'."""
    return os.environ.get(ENV_VAR, FALLBACK_NAMESPACE)


def robot_namespace_argument():
    return DeclareLaunchArgument(
        "robot_namespace",
        default_value=default_robot_namespace(),
        description=f"Robot namespace (env {ENV_VAR}, default '{FALLBACK_NAMESPACE}'); "
        "empty = no namespace. It must match the one configured on the Create 3.",
    )


def resolve_namespace(context):
    """Return the normalized namespace without slashes at the ends ('' = none)."""
    raw = LaunchConfiguration("robot_namespace").perform(context).strip().strip("/")
    if raw and not _NAMESPACE_RE.match(raw):
        raise RuntimeError(
            f"robot_namespace:='{raw}' is not valid: use letters, digits and '_' "
            "(starting with a letter), e.g. r2."
        )
    return raw


def namespaced(namespace, actions):
    """Group `actions` under `namespace` (PushRosNamespace); with '' return them unchanged."""
    if not namespace:
        return list(actions)
    return [GroupAction([PushRosNamespace(namespace), *actions])]


def tf_remappings(namespace):
    """TF remaps so nodes use <ns>/tf and <ns>/tf_static (the Create 3 publishes them there).

    The targets are relative: they resolve under the node namespace. Without a namespace there are no remaps.
    """
    if not namespace:
        return []
    return [("/tf", "tf"), ("/tf_static", "tf_static")]


def rewrite_yaml(yaml_path, namespace):
    """YAML for nodes under `namespace`: RewrittenYaml(root_key=ns). With '' the file is returned unchanged.

    A parameters YAML starts with the node name (`slam_toolbox:`). Under a namespace, ROS expects
    `/r2/slam_toolbox`, so RewrittenYaml wraps the content with the namespace key.
    """
    if not namespace:
        return yaml_path
    from nav2_common.launch import RewrittenYaml

    return RewrittenYaml(
        source_file=yaml_path, root_key=namespace, param_rewrites={}, convert_types=True
    )


def substitute_namespace_markers(source_file, namespace):
    """ReplaceString that turns '/<robot_namespace>' into '/<ns>' ('' if there is no namespace).

    Used with the .rviz files: topics are written as '/<robot_namespace>/scan' and become '/r2/scan'.
    It ALWAYS returns a ReplaceString, also with namespace '' (the marker becomes '' and
    '/<robot_namespace>/scan' becomes '/scan', never '//scan').
    """
    from nav2_common.launch import ReplaceString

    return ReplaceString(
        source_file=source_file,
        replacements={"/<robot_namespace>": f"/{namespace}" if namespace else ""},
    )
