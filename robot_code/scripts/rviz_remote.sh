#!/usr/bin/env bash
# Opens RViz on this machine (your PC) to view the real robot running on the Pi.
#
# On the Pi, launch first, without RViz (the Pi does not need a display):
#   ros2 launch mrobot_bringup mapping.launch.py lidar_model:=rplidar_c1 rviz:=false
#   ros2 launch mrobot_bringup navigation.launch.py map_yaml:=<path> lidar_model:=rplidar_c1 rviz:=false
#
# Both machines must be on the same network and use the same ROS_DOMAIN_ID and RMW_IMPLEMENTATION.
#
# Usage:  scripts/rviz_remote.sh [mapping|navigation] [--namespace NS] [--domain ID] [--rmw NAME]
#   mapping|navigation  RViz configuration to use (default: mapping)
#   --namespace         robot namespace (default: $CREATE3_ROBOT_NAMESPACE if set, otherwise r2; empty = none)
#   --domain            ROS_DOMAIN_ID (default: the one you already exported; it must match the Pi's)
#   --rmw               RMW_IMPLEMENTATION (default: the one you already exported; it must match the Pi's)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"   # robot_code/
NAMESPACE="${CREATE3_ROBOT_NAMESPACE-r2}"
CONFIG="mapping"

die() { echo "ERROR: $*" >&2; exit 1; }

usage() {
  sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  arg="$1"; shift
  case "$arg" in
    mapping|navigation) CONFIG="${arg}" ;;
    --namespace) [ $# -gt 0 ] || die "--namespace needs a value (use '' for none)"; NAMESPACE="$1"; shift ;;
    --domain) [ $# -gt 0 ] || die "--domain needs a value"; export ROS_DOMAIN_ID="$1"; shift ;;
    --rmw) [ $# -gt 0 ] || die "--rmw needs a value"; export RMW_IMPLEMENTATION="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: ${arg} (use --help)" ;;
  esac
done

NAMESPACE="${NAMESPACE#/}"; NAMESPACE="${NAMESPACE%/}"

SRC_RVIZ="${WS_ROOT}/src/mrobot_bringup/rviz/${CONFIG}.rviz"
[ -f "${SRC_RVIZ}" ] || die "${SRC_RVIZ} does not exist"

# set -u breaks with ROS's setup.bash files; it is only disabled while they are sourced.
set +u
[ -f /opt/ros/jazzy/setup.bash ] || die "cannot find /opt/ros/jazzy/setup.bash"
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [ -f "${WS_ROOT}/install/setup.bash" ]; then
  # shellcheck disable=SC1091
  source "${WS_ROOT}/install/setup.bash"
fi
set -u

command -v rviz2 >/dev/null || die "rviz2 is not installed (sudo apt install ros-jazzy-rviz2)"

# The .rviz uses the /<robot_namespace> marker; the launch file replaces it, here we do it with sed.
# Portable temporary folder (mktemp --suffix only exists in GNU).
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
TMP_RVIZ="${TMP_DIR}/${CONFIG}.rviz"
if [ -n "${NAMESPACE}" ]; then
  sed "s#/<robot_namespace>#/${NAMESPACE}#g" "${SRC_RVIZ}" > "${TMP_RVIZ}"
  REMAPS=(-r "/tf:=/${NAMESPACE}/tf" -r "/tf_static:=/${NAMESPACE}/tf_static")
else
  sed "s#/<robot_namespace>##g" "${SRC_RVIZ}" > "${TMP_RVIZ}"
  REMAPS=()
fi

echo "RViz: config=${CONFIG} namespace='${NAMESPACE}' ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0} RMW=${RMW_IMPLEMENTATION:-default}"
# ${REMAPS[@]+...} avoids the 'unbound variable' error with the empty array in old bash.
rviz2 -d "${TMP_RVIZ}" --ros-args ${REMAPS[@]+"${REMAPS[@]}"}
