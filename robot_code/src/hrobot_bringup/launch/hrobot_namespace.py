"""Utilidades compartidas por los launch de hrobot_bringup (manejo del namespace del robot).

No es un launch: es un módulo Python normal. Los launch añaden su propia carpeta a sys.path y lo importan.

Diseño del namespace (se aplica UNA sola vez, para evitar /r2/r2/...):
  * Cada launch declara `robot_namespace` y aplica el namespace él mismo, solo a los nodos que crea
    directamente (GroupAction + PushRosNamespace, ver `namespaced`).
  * Namespace vacío = no se aplica nada (simulación, sin namespace).
  * El Create 3 real vive en /r2 (publica /r2/odom, /r2/tf, /r2/tf_static y escucha /r2/cmd_vel).

También incluye rewrite_yaml() y substitute_namespace_markers() para los YAML y los .rviz con namespace.
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
    """Variable de entorno CREATE3_ROBOT_NAMESPACE si existe (incluso vacía = sin namespace); si no, 'r2'."""
    return os.environ.get(ENV_VAR, FALLBACK_NAMESPACE)


def robot_namespace_argument():
    return DeclareLaunchArgument(
        "robot_namespace",
        default_value=default_robot_namespace(),
        description=f"Namespace del robot (env {ENV_VAR}, por defecto '{FALLBACK_NAMESPACE}'); "
        "vacío = sin namespace. Debe coincidir con el configurado en el Create 3.",
    )


def resolve_namespace(context):
    """Devuelve el namespace normalizado, sin barras en los extremos ('' = ninguno)."""
    raw = LaunchConfiguration("robot_namespace").perform(context).strip().strip("/")
    if raw and not _NAMESPACE_RE.match(raw):
        raise RuntimeError(
            f"robot_namespace:='{raw}' no es válido: usa letras, dígitos y '_' "
            "(empezando por letra), por ejemplo r2."
        )
    return raw


def namespaced(namespace, actions):
    """Agrupa `actions` bajo `namespace` (PushRosNamespace); con '' las devuelve sin cambios."""
    if not namespace:
        return list(actions)
    return [GroupAction([PushRosNamespace(namespace), *actions])]


def tf_remappings(namespace):
    """Remaps de TF para que los nodos usen <ns>/tf y <ns>/tf_static (el Create 3 los publica ahí).

    Los destinos son relativos: se resuelven bajo el namespace del nodo. Sin namespace no hay remaps.
    """
    if not namespace:
        return []
    return [("/tf", "tf"), ("/tf_static", "tf_static")]


def rewrite_yaml(yaml_path, namespace):
    """YAML para nodos bajo `namespace`: RewrittenYaml(root_key=ns). Con '' devuelve el archivo sin cambios.

    Un YAML de parámetros empieza por el nombre del nodo (`slam_toolbox:`). Bajo un namespace, ROS espera
    `/r2/slam_toolbox`, así que RewrittenYaml envuelve el contenido con la clave del namespace.
    """
    if not namespace:
        return yaml_path
    from nav2_common.launch import RewrittenYaml

    return RewrittenYaml(
        source_file=yaml_path, root_key=namespace, param_rewrites={}, convert_types=True
    )


def substitute_namespace_markers(source_file, namespace):
    """ReplaceString que convierte '/<robot_namespace>' en '/<ns>' ('' si no hay namespace).

    Se usa con los .rviz: los topics se escriben como '/<robot_namespace>/scan' y quedan '/r2/scan'.
    Siempre devuelve un ReplaceString, también con namespace '' (el marcador pasa a '' y
    '/<robot_namespace>/scan' queda '/scan', nunca '//scan').
    """
    from nav2_common.launch import ReplaceString

    return ReplaceString(
        source_file=source_file,
        replacements={"/<robot_namespace>": f"/{namespace}" if namespace else ""},
    )
