#!/usr/bin/env bash
# Prepara la Raspberry Pi 5 para ejecutar este workspace. NO compila nada.
#
# Requisito previo: Ubuntu con ROS 2 Jazzy ya instalado en /opt/ros/jazzy (este script NO instala ROS)
# y con git, colcon y rosdep ya instalados (este script tampoco los instala).
# Es idempotente: se puede volver a ejecutar sin romper nada.
#
# Qué hace:
#   1. Inicializa/actualiza rosdep.
#   2. Red ROS 2: fija ROS_DOMAIN_ID y RMW_IMPLEMENTATION (deben coincidir con los del Create 3),
#      los guarda en ~/.config/materialenbuddy/ros_net.env y los carga desde ~/.bashrc (bloque marcado, una vez).
#   3. Permisos del puerto serie: grupo dialout + regla udev con symlink /dev/ldlidar.
#   4. Instala con rosdep las dependencias de sistema del robot real (no las de la simulación).
#
# El driver del LD19 (ldlidar_stl_ros2) ya está en src/: no se clona nada.
# Compilar queda a tu cargo; al terminar, el script muestra el comando.
#
# Uso:  scripts/setup_pi.sh [--skip-udev] [--skip-net] [--domain-id N] [--rmw NOMBRE]
#   --skip-udev     no añade tu usuario a dialout ni instala la regla udev (no existirá /dev/ldlidar:
#                   pasa el puerto real, p. ej. lidar_port:=/dev/ttyUSB0)
#   --skip-net      no toca ROS_DOMAIN_ID / RMW_IMPLEMENTATION
#   --domain-id N   dominio ROS (def: $ROS_DOMAIN_ID si existe, si no 0)
#   --rmw NOMBRE    middleware: rmw_fastrtps_cpp | rmw_cyclonedds_cpp (def: $RMW_IMPLEMENTATION si existe,
#                   si no rmw_fastrtps_cpp)
# Variable opcional:
#   ROS_DISTRO_NAME  distribución de ROS (def: jazzy)

set -euo pipefail

ROS_DISTRO_NAME="${ROS_DISTRO_NAME:-jazzy}"
UDEV_RULE="/etc/udev/rules.d/99-ldlidar.rules"
# CP2102 (USB-serie habitual del LD19). Verifícalo con `lsusb` y ajusta si tu adaptador es otro.
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

# Paquetes del robot real: rosdep solo instala las dependencias de estos (no las de la simulación).
REAL_ROBOT_PATHS=(src/hrobot_bringup src/irobot_create_description src/ldlidar_stl_ros2)

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
    --domain-id) [ $# -gt 0 ] || { echo "--domain-id requiere un valor" >&2; exit 2; }; DOMAIN_ID="$1"; shift ;;
    --rmw) [ $# -gt 0 ] || { echo "--rmw requiere un valor" >&2; exit 2; }; RMW_NAME="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento desconocido: $arg (usa --help)" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ "${DOMAIN_ID}" =~ ^[0-9]+$ ]] && [ "${DOMAIN_ID}" -le 232 ] || { echo "ROS_DOMAIN_ID inválido: ${DOMAIN_ID} (0-232)" >&2; exit 2; }
case "${RMW_NAME}" in
  rmw_fastrtps_cpp|rmw_cyclonedds_cpp) ;;
  *) echo "RMW no soportado: ${RMW_NAME} (usa rmw_fastrtps_cpp o rmw_cyclonedds_cpp)" >&2; exit 2 ;;
esac

# Raíz del workspace = carpeta robot_code (este script vive en robot_code/scripts/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

[ "$(id -u)" -ne 0 ] || die "No lo ejecutes como root; usa tu usuario (el script llama a sudo cuando hace falta)."
[ -f "/opt/ros/${ROS_DISTRO_NAME}/setup.bash" ] || die "No se encuentra /opt/ros/${ROS_DISTRO_NAME}/setup.bash. Instala ROS 2 ${ROS_DISTRO_NAME} primero."
for p in "${REAL_ROBOT_PATHS[@]}"; do
  [ -d "$p" ] || die "No se encuentra ${p} en ${REPO_ROOT}."
done

log "Inicializando rosdep"
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update --rosdistro "${ROS_DISTRO_NAME}"

# setup.bash de ROS usa variables sin definir: desactivar -u mientras se carga.
set +u
# shellcheck disable=SC1090
source "/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
set -u

if [ "${SKIP_NET}" -eq 0 ]; then
  log "Red ROS 2 (ROS_DOMAIN_ID=${DOMAIN_ID}, RMW_IMPLEMENTATION=${RMW_NAME})"
  # Instala el middleware elegido (rmw_fastrtps_cpp ya viene con ros-base; cyclonedds no siempre).
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
  # Aplicar también a este proceso (rosdep) y avisar para el robot.
  export ROS_DOMAIN_ID="${DOMAIN_ID}" RMW_IMPLEMENTATION="${RMW_NAME}"
  echo "Guardado en ${NET_FILE}. Abre una terminal nueva (o 'source ~/.bashrc')."
  echo "IMPORTANTE: el Create 3 debe usar el mismo RMW (interfaz web > Application > ROS 2) y su ROS_DOMAIN_ID"
  echo "debe ser ${DOMAIN_ID}. Reinicia la aplicación del Create 3 tras cambiarlos."
  if grep -qxF "# >>> hrobot ros_net >>>" "${BASHRC}"; then
    echo "AVISO: ${BASHRC} también tiene el bloque 'hrobot ros_net' de una instalación anterior. Si sus valores" >&2
    echo "       difieren de los de arriba, elimínalo: el que aparezca más abajo en el archivo es el que vale." >&2
  fi
else
  log "Omitiendo configuración de red ROS (--skip-net)"
fi

if [ "${SKIP_UDEV}" -eq 0 ]; then
  log "Permisos del puerto serie (dialout + udev /dev/ldlidar)"
  if ! id -nG "${USER}" | tr ' ' '\n' | grep -qx dialout; then
    sudo usermod -aG dialout "${USER}"
    echo "Añadido ${USER} al grupo dialout: cierra sesión y vuelve a entrar para que surta efecto."
  fi
  if [ ! -f "${UDEV_RULE}" ] || [ "$(cat "${UDEV_RULE}")" != "${UDEV_CONTENT}" ]; then
    printf '%s\n' "${UDEV_CONTENT}" | sudo tee "${UDEV_RULE}" >/dev/null
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "Regla udev instalada en ${UDEV_RULE}. Reconecta el LiDAR; debería aparecer /dev/ldlidar."
  fi
  if command -v lsusb >/dev/null 2>&1 && ! lsusb | grep -qi "${UDEV_VENDOR}:${UDEV_PRODUCT}"; then
    echo "AVISO: lsusb no muestra ningún dispositivo ${UDEV_VENDOR}:${UDEV_PRODUCT} (CP2102). Con el LiDAR conectado," >&2
    echo "       revisa el identificador real con 'lsusb' y ajusta UDEV_VENDOR / UDEV_PRODUCT en este script." >&2
  fi
else
  log "Omitiendo permisos udev (--skip-udev)"
fi

log "Instalando dependencias del robot real con rosdep (no compila nada)"
rosdep install --from-paths "${REAL_ROBOT_PATHS[@]}" --ignore-src -y --rosdistro "${ROS_DISTRO_NAME}"

log "Listo (no se ha compilado nada)"
cat <<EOF
Siguientes pasos:
  cd ${REPO_ROOT}
  colcon build --symlink-install --parallel-workers 2 --packages-up-to hrobot_bringup
      # 2 workers para no agotar la RAM de la Pi; --packages-up-to deja fuera la simulación
  source ${REPO_ROOT}/install/setup.bash
  ls -l /dev/ldlidar            # o /dev/ttyUSB0 si no usas la regla udev
  echo \$ROS_DOMAIN_ID \$RMW_IMPLEMENTATION   # deben coincidir con los del Create 3
  ros2 topic list | grep -E '/r2/(odom|cmd_vel)'   # comprueba los topics del Create 3
  ros2 launch hrobot_bringup mapping.launch.py lidar_port:=/dev/ldlidar
  # otro robot sin tocar el entorno: ... mapping.launch.py robot_namespace:=r3
Namespace en esta terminal: ${CREATE3_ROBOT_NAMESPACE-r2} (variable CREATE3_ROBOT_NAMESPACE, o 'r2' por defecto).
Todo el stack cuelga de él: /r2/scan, /r2/map, /r2/cmd_vel... El namespace del Create 3 se cambia en su interfaz web.
EOF
