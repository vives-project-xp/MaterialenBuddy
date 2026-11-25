#!/usr/bin/env bash
# Saves the map that slam_toolbox is building (mapping.launch.py must be running).
#
# It generates in <maps_dir> the two formats used by the map -> navigate flow:
#   <name>.posegraph + <name>.data   slam_toolbox pose graph (to resume mapping)
#   <name>.yaml + <name>.pgm         map image (to NAVIGATE with Nav2)
#
# Usage:  scripts/save_map.sh <name> [--maps-dir DIR] [--namespace NS] [--force]
#                                    [--pull USER@HOST] [--remote-ws DIR]
#   <name>         letters, digits, '_' and '-' only (no path or extension)
#   --maps-dir     output folder on THIS machine (default: <robot_code>/maps)
#   --namespace    robot namespace (default: $CREATE3_ROBOT_NAMESPACE if set, otherwise r2; empty = none)
#   --force        overwrite an existing map with that name
#   --pull         slam_toolbox runs on ANOTHER machine (the Pi): the files are saved there, in
#                  <remote-ws>/maps, and then copied with scp to --maps-dir. Needs ssh to that host.
#   --remote-ws    robot_code folder on the other machine (default: ~/MaterialenBuddy/robot_code); only with --pull
#
# slam_toolbox writes the files on the machine where it runs. Without --pull, run this script on that same
# machine; the services answer over the network from another one, but the files would end up on the remote disk.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"   # robot_code/
MAPS_DIR="${WS_ROOT}/maps"
NAMESPACE="${CREATE3_ROBOT_NAMESPACE-r2}"
FORCE=0
NAME=""
PULL=""
REMOTE_WS="~/MaterialenBuddy/robot_code"
EXTS=(posegraph data yaml pgm)

die() { echo "ERROR: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  arg="$1"; shift
  case "$arg" in
    --maps-dir) [ $# -gt 0 ] || die "--maps-dir needs a value"; MAPS_DIR="$1"; shift ;;
    --namespace) [ $# -gt 0 ] || die "--namespace needs a value (use '' for none)"; NAMESPACE="$1"; shift ;;
    --pull) [ $# -gt 0 ] || die "--pull needs user@host"; PULL="$1"; shift ;;
    --remote-ws) [ $# -gt 0 ] || die "--remote-ws needs a value"; REMOTE_WS="$1"; shift ;;
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*) die "unknown option: ${arg}" ;;
    *) [ -z "${NAME}" ] || die "only one map name is accepted"; NAME="${arg}" ;;
  esac
done

[ -n "${NAME}" ] || die "missing map name. Usage: save_map.sh <name> [--maps-dir DIR] [--namespace NS] [--force] [--pull user@host]"
[[ "${NAME}" =~ ^[A-Za-z0-9_-]+$ ]] || die "invalid name '${NAME}': use only letters, digits, '_' and '-'"

NAMESPACE="${NAMESPACE#/}"; NAMESPACE="${NAMESPACE%/}"
PREFIX=""
[ -z "${NAMESPACE}" ] || PREFIX="/${NAMESPACE}"

command -v ros2 >/dev/null || die "ros2 is not in the PATH: source /opt/ros/jazzy/setup.bash and the workspace"

mkdir -p "${MAPS_DIR}"
MAPS_DIR="$(cd "${MAPS_DIR}" && pwd)"   # absolute path
LOCAL_BASE="${MAPS_DIR}/${NAME}"

if [ "${FORCE}" -eq 0 ]; then
  for ext in "${EXTS[@]}"; do
    [ ! -e "${LOCAL_BASE}.${ext}" ] || die "${LOCAL_BASE}.${ext} already exists (use --force to overwrite)"
  done
fi

# BASE = path (without extension) given to slam_toolbox: it must exist on the machine where it runs.
if [ -n "${PULL}" ]; then
  command -v ssh >/dev/null && command -v scp >/dev/null || die "--pull needs ssh and scp"
  # slam_toolbox does not expand '~': it is resolved to an absolute path on the other machine.
  REMOTE_WS_ABS="$(ssh "${PULL}" "cd ${REMOTE_WS} && pwd")" \
    || die "could not enter '${REMOTE_WS}' on ${PULL} (is --remote-ws correct? does ssh work?)"
  REMOTE_MAPS="${REMOTE_WS_ABS}/maps"
  ssh "${PULL}" "mkdir -p '${REMOTE_MAPS}'" || die "could not create ${REMOTE_MAPS} on ${PULL}"
  if [ "${FORCE}" -eq 0 ]; then
    for ext in "${EXTS[@]}"; do
      ssh "${PULL}" "[ ! -e '${REMOTE_MAPS}/${NAME}.${ext}' ]" \
        || die "${PULL}:${REMOTE_MAPS}/${NAME}.${ext} already exists (use --force to overwrite)"
    done
  fi
  BASE="${REMOTE_MAPS}/${NAME}"
else
  BASE="${LOCAL_BASE}"
  if ! pgrep -f async_slam_toolbox_node >/dev/null 2>&1; then
    echo "WARNING: no slam_toolbox is running on this machine. If it runs on the Pi, the files would be" >&2
    echo "         saved there: use --pull user@host (or run this script on the Pi)." >&2
  fi
fi

SER="${PREFIX}/slam_toolbox/serialize_map"
SAVE="${PREFIX}/slam_toolbox/save_map"
timeout 10 ros2 service list 2>/dev/null | grep -qx "${SER}" \
  || die "service ${SER} does not exist: is mapping.launch.py running and is the namespace '${NAMESPACE}'?"

# Calls a service and shows its response (on failure, it shows the reason).
call_service() {
  local service="$1" type="$2" request="$3" out
  out="$(timeout 60 ros2 service call "${service}" "${type}" "${request}" 2>&1)" \
    || { echo "${out}" >&2; die "the call to ${service} failed"; }
  echo "${out}" | sed -n '/response/,$p' | sed 's/^/      /'
}

echo "[1/2] Saving pose graph to ${BASE}.posegraph/.data ..."
call_service "${SER}" slam_toolbox/srv/SerializePoseGraph "{filename: '${BASE}'}"

echo "[2/2] Saving image to ${BASE}.yaml/.pgm ..."
call_service "${SAVE}" slam_toolbox/srv/SaveMap "{name: {data: '${BASE}'}}"

if [ -n "${PULL}" ]; then
  missing=0
  for ext in "${EXTS[@]}"; do
    ssh "${PULL}" "[ -s '${BASE}.${ext}' ]" || { echo "ERROR: ${PULL}:${BASE}.${ext} was not generated" >&2; missing=1; }
  done
  [ "${missing}" -eq 0 ] || die "the map was not fully saved in ${PULL}:${REMOTE_MAPS}"
  echo "[+] Copying from ${PULL} to ${MAPS_DIR} ..."
  for ext in "${EXTS[@]}"; do
    scp -q "${PULL}:${BASE}.${ext}" "${LOCAL_BASE}.${ext}" || die "scp of ${BASE}.${ext} failed"
  done
fi

missing=0
for ext in "${EXTS[@]}"; do
  if [ ! -s "${LOCAL_BASE}.${ext}" ]; then echo "ERROR: ${LOCAL_BASE}.${ext} was not generated" >&2; missing=1; fi
done
if [ "${missing}" -ne 0 ]; then
  [ -n "${PULL}" ] || echo "The services answered but there are no files here: slam_toolbox runs on another machine and saved them there." >&2
  [ -n "${PULL}" ] || echo "Repeat with --pull user@host, or copy the files by hand with scp." >&2
  die "the map was not fully saved in ${MAPS_DIR}"
fi

echo
echo "Map '${NAME}' saved in ${MAPS_DIR}:"
ls -l "${LOCAL_BASE}".{posegraph,data,yaml,pgm}
