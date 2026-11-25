#!/usr/bin/env bash
# Prepares the Raspberry Pi 5 to run this workspace. It does NOT build anything.
#
# Prerequisite: Ubuntu with ROS 2 Jazzy already installed in /opt/ros/jazzy (this script does NOT install ROS)
# and with git, colcon and rosdep already installed (this script does not install them either).
# It is idempotent: it can be run again without breaking anything.
#
# What it does:
#   1. Initializes/updates rosdep.
#   2. ROS 2 network: sets ROS_DOMAIN_ID and RMW_IMPLEMENTATION (they must match the Create 3's),
#      saves them in ~/.config/materialenbuddy/ros_net.env and loads them from ~/.bashrc (a marked block, once).
#   3. Serial port permissions: dialout group + a udev rule with the /dev/ldlidar symlink.
#   4. Installs the real robot's system dependencies with rosdep (not the simulation's).
#
# The LD19 driver (ldlidar_stl_ros2) is already in src/: nothing is cloned.
# Building is up to you; when it finishes, the script prints the command.
#
# Usage:  scripts/setup_pi.sh [--skip-udev] [--skip-net] [--domain-id N] [--rmw NAME]
#   --skip-udev     do not add your user to dialout or install the udev rule (/dev/ldlidar will not exist:
#                   pass the real port, e.g. lidar_port:=/dev/ttyUSB0)
#   --skip-net      do not touch ROS_DOMAIN_ID / RMW_IMPLEMENTATION
#   --domain-id N   ROS domain (default: $ROS_DOMAIN_ID if set, otherwise 0)
#   --rmw NAME      middleware: rmw_fastrtps_cpp | rmw_cyclonedds_cpp (default: $RMW_IMPLEMENTATION if set,
#                   otherwise rmw_fastrtps_cpp)
# Optional variable:
#   ROS_DISTRO_NAME  ROS distribution (default: jazzy)

set -euo pipefail

ROS_DISTRO_NAME="${ROS_DISTRO_NAME:-jazzy}"
UDEV_RULE="/etc/udev/rules.d/99-ldlidar.rules"
# CP2102 (the usual USB-serial chip of the LD19). Check it with `lsusb` and adjust if your adapter is another one.
UDEV_VENDOR="10c4"
UDEV_PRODUCT="ea60"
UDEV_CONTENT="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${UDEV_VENDOR}\", ATTRS{idProduct}==\"${UDEV_PRODUCT}\", SYMLINK+=\"ldlidar\", GROUP=\"dialout\", MODE=\"0660\""

NET_DIR="${HOME}/.config/materialenbuddy"
NET_FILE="${NET_DIR}/ros_net.env"
BASHRC="${HOME}/.bashrc"
NET_BEGIN="# >>> materialenbuddy ros_net >>>"
NET_END="# <<< materialenbuddy ros_net <<<"
DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
RMW_NAME="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

# Real robot packages: rosdep only installs the dependencies of these (not the simulation's).
REAL_ROBOT_PATHS=(src/mrobot_bringup src/irobot_create_description src/ldlidar_stl_ros2)

SKIP_UDEV=0
SKIP_NET=0

usage() {
  sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  arg="$1"; shift
  case "$arg" in
    --skip-udev) SKIP_UDEV=1 ;;
    --skip-net) SKIP_NET=1 ;;
    --domain-id) [ $# -gt 0 ] || { echo "--domain-id needs a value" >&2; exit 2; }; DOMAIN_ID="$1"; shift ;;
    --rmw) [ $# -gt 0 ] || { echo "--rmw needs a value" >&2; exit 2; }; RMW_NAME="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $arg (use --help)" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ "${DOMAIN_ID}" =~ ^[0-9]+$ ]] && [ "${DOMAIN_ID}" -le 232 ] || { echo "Invalid ROS_DOMAIN_ID: ${DOMAIN_ID} (0-232)" >&2; exit 2; }
case "${RMW_NAME}" in
  rmw_fastrtps_cpp|rmw_cyclonedds_cpp) ;;
  *) echo "Unsupported RMW: ${RMW_NAME} (use rmw_fastrtps_cpp or rmw_cyclonedds_cpp)" >&2; exit 2 ;;
esac

# Workspace root = the robot_code folder (this script lives in robot_code/scripts/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

[ "$(id -u)" -ne 0 ] || die "Do not run it as root; use your own user (the script calls sudo when needed)."
[ -f "/opt/ros/${ROS_DISTRO_NAME}/setup.bash" ] || die "/opt/ros/${ROS_DISTRO_NAME}/setup.bash not found. Install ROS 2 ${ROS_DISTRO_NAME} first."
for p in "${REAL_ROBOT_PATHS[@]}"; do
  [ -d "$p" ] || die "${p} not found in ${REPO_ROOT}."
done

log "Initializing rosdep"
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update --rosdistro "${ROS_DISTRO_NAME}"

# ROS's setup.bash uses unset variables: disable -u while it is sourced.
set +u
# shellcheck disable=SC1090
source "/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
set -u

if [ "${SKIP_NET}" -eq 0 ]; then
  log "ROS 2 network (ROS_DOMAIN_ID=${DOMAIN_ID}, RMW_IMPLEMENTATION=${RMW_NAME})"
  # Install the chosen middleware (rmw_fastrtps_cpp already comes with ros-base; cyclonedds does not always).
  sudo apt-get install -y "ros-${ROS_DISTRO_NAME}-${RMW_NAME//_/-}"
  mkdir -p "${NET_DIR}"
  printf 'export ROS_DOMAIN_ID=%s\nexport RMW_IMPLEMENTATION=%s\n' "${DOMAIN_ID}" "${RMW_NAME}" > "${NET_FILE}"
  touch "${BASHRC}"
  if ! grep -qxF "${NET_BEGIN}" "${BASHRC}"; then
    if [ -s "${BASHRC}" ] && [ -n "$(tail -c 1 "${BASHRC}")" ]; then printf '\n' >> "${BASHRC}"; fi
    {
      echo "${NET_BEGIN}"
      echo "[ -f \"${NET_FILE}\" ] && . \"${NET_FILE}\""
      echo "${NET_END}"
    } >> "${BASHRC}"
  fi
  # Apply it to this process as well (rosdep) and warn about the robot.
  export ROS_DOMAIN_ID="${DOMAIN_ID}" RMW_IMPLEMENTATION="${RMW_NAME}"
  echo "Saved in ${NET_FILE}. Open a new terminal (or 'source ~/.bashrc')."
  echo "IMPORTANT: the Create 3 must use the same RMW (web UI > Application > ROS 2) and its ROS_DOMAIN_ID"
  echo "must be ${DOMAIN_ID}. Restart the Create 3 application after changing them."
  if grep -qxF "# >>> hrobot ros_net >>>" "${BASHRC}"; then
    echo "WARNING: ${BASHRC} also has the 'hrobot ros_net' block from a previous installation. If its values" >&2
    echo "         differ from the ones above, remove it: the block that appears lower in the file is the one that applies." >&2
  fi
else
  log "Skipping ROS network configuration (--skip-net)"
fi

if [ "${SKIP_UDEV}" -eq 0 ]; then
  log "Serial port permissions (dialout + udev /dev/ldlidar)"
  if ! id -nG "${USER}" | tr ' ' '\n' | grep -qx dialout; then
    sudo usermod -aG dialout "${USER}"
    echo "Added ${USER} to the dialout group: log out and back in for it to take effect."
  fi
  if [ ! -f "${UDEV_RULE}" ] || [ "$(cat "${UDEV_RULE}")" != "${UDEV_CONTENT}" ]; then
    printf '%s\n' "${UDEV_CONTENT}" | sudo tee "${UDEV_RULE}" >/dev/null
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "udev rule installed in ${UDEV_RULE}. Reconnect the LiDAR; /dev/ldlidar should appear."
  fi
  if command -v lsusb >/dev/null 2>&1 && ! lsusb | grep -qi "${UDEV_VENDOR}:${UDEV_PRODUCT}"; then
    echo "WARNING: lsusb shows no ${UDEV_VENDOR}:${UDEV_PRODUCT} device (CP2102). With the LiDAR connected," >&2
    echo "         check the real identifier with 'lsusb' and adjust UDEV_VENDOR / UDEV_PRODUCT in this script." >&2
  fi
else
  log "Skipping udev permissions (--skip-udev)"
fi

log "Installing the real robot dependencies with rosdep (builds nothing)"
rosdep install --from-paths "${REAL_ROBOT_PATHS[@]}" --ignore-src -y --rosdistro "${ROS_DISTRO_NAME}"

log "Done (nothing was built)"
cat <<EOF
Next steps:
  cd ${REPO_ROOT}
  colcon build --symlink-install --parallel-workers 2 --packages-up-to mrobot_bringup
      # 2 workers so the Pi does not run out of RAM; --packages-up-to leaves the simulation out
  source ${REPO_ROOT}/install/setup.bash
  ls -l /dev/ldlidar            # or /dev/ttyUSB0 if you do not use the udev rule
  echo \$ROS_DOMAIN_ID \$RMW_IMPLEMENTATION   # they must match the Create 3's
  ros2 topic list | grep -E '/r2/(odom|cmd_vel)'   # check the Create 3 topics
  ros2 launch mrobot_bringup mapping.launch.py lidar_port:=/dev/ldlidar
  # another robot without touching the environment: ... mapping.launch.py robot_namespace:=r3
Namespace in this terminal: ${CREATE3_ROBOT_NAMESPACE-r2} (variable CREATE3_ROBOT_NAMESPACE, or 'r2' by default).
The whole stack hangs from it: /r2/scan, /r2/map, /r2/cmd_vel... The Create 3 namespace is changed in its web UI.
EOF
