#!/usr/bin/env bash
# Guarda el mapa que slam_toolbox está construyendo (mapping.launch.py debe estar corriendo).
#
# Genera en <maps_dir> los dos formatos que usa el flujo mapear -> navegar:
#   <nombre>.posegraph + <nombre>.data   grafo de poses de slam_toolbox (para retomar el mapeo)
#   <nombre>.yaml + <nombre>.pgm         imagen del mapa (para NAVEGAR con Nav2, paso 4)
#
# Uso:  scripts/save_map.sh <nombre> [--maps-dir DIR] [--namespace NS] [--force]
#                                    [--pull USUARIO@HOST] [--remote-ws DIR]
#   <nombre>       solo letras, dígitos, '_' y '-' (sin ruta ni extensión)
#   --maps-dir     carpeta de salida en ESTA máquina (def: <robot_code>/maps)
#   --namespace    namespace del robot (def: $CREATE3_ROBOT_NAMESPACE si existe, si no r2; vacío = ninguno)
#   --force        sobrescribe un mapa existente con ese nombre
#   --pull         slam_toolbox corre en OTRA máquina (la Pi): los archivos se guardan allí, en
#                  <remote-ws>/maps, y luego se copian con scp a --maps-dir. Necesita ssh a ese host.
#   --remote-ws    carpeta robot_code en la otra máquina (def: ~/MaterialenBuddy/robot_code); solo con --pull
#
# slam_toolbox escribe los archivos en la máquina donde corre. Sin --pull, ejecuta este script en esa misma
# máquina; los servicios responden por red desde otra, pero los archivos acabarían en el disco remoto.

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
    --maps-dir) [ $# -gt 0 ] || die "--maps-dir necesita un valor"; MAPS_DIR="$1"; shift ;;
    --namespace) [ $# -gt 0 ] || die "--namespace necesita un valor (usa '' para ninguno)"; NAMESPACE="$1"; shift ;;
    --pull) [ $# -gt 0 ] || die "--pull necesita usuario@host"; PULL="$1"; shift ;;
    --remote-ws) [ $# -gt 0 ] || die "--remote-ws necesita un valor"; REMOTE_WS="$1"; shift ;;
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*) die "opción desconocida: ${arg}" ;;
    *) [ -z "${NAME}" ] || die "solo se admite un nombre de mapa"; NAME="${arg}" ;;
  esac
done

[ -n "${NAME}" ] || die "falta el nombre del mapa. Uso: save_map.sh <nombre> [--maps-dir DIR] [--namespace NS] [--force] [--pull usuario@host]"
[[ "${NAME}" =~ ^[A-Za-z0-9_-]+$ ]] || die "nombre inválido '${NAME}': usa solo letras, dígitos, '_' y '-'"

NAMESPACE="${NAMESPACE#/}"; NAMESPACE="${NAMESPACE%/}"
PREFIX=""
[ -z "${NAMESPACE}" ] || PREFIX="/${NAMESPACE}"

command -v ros2 >/dev/null || die "ros2 no está en el PATH: haz source de /opt/ros/jazzy/setup.bash y del workspace"

mkdir -p "${MAPS_DIR}"
MAPS_DIR="$(cd "${MAPS_DIR}" && pwd)"   # ruta absoluta
LOCAL_BASE="${MAPS_DIR}/${NAME}"

if [ "${FORCE}" -eq 0 ]; then
  for ext in "${EXTS[@]}"; do
    [ ! -e "${LOCAL_BASE}.${ext}" ] || die "${LOCAL_BASE}.${ext} ya existe (usa --force para sobrescribir)"
  done
fi

# BASE = ruta (sin extensión) que recibe slam_toolbox: debe existir en la máquina donde corre.
if [ -n "${PULL}" ]; then
  command -v ssh >/dev/null && command -v scp >/dev/null || die "--pull necesita ssh y scp"
  # slam_toolbox no expande '~': se resuelve a ruta absoluta en la otra máquina.
  REMOTE_WS_ABS="$(ssh "${PULL}" "cd ${REMOTE_WS} && pwd")" \
    || die "no pude entrar en '${REMOTE_WS}' en ${PULL} (¿--remote-ws correcto? ¿ssh funciona?)"
  REMOTE_MAPS="${REMOTE_WS_ABS}/maps"
  ssh "${PULL}" "mkdir -p '${REMOTE_MAPS}'" || die "no pude crear ${REMOTE_MAPS} en ${PULL}"
  if [ "${FORCE}" -eq 0 ]; then
    for ext in "${EXTS[@]}"; do
      ssh "${PULL}" "[ ! -e '${REMOTE_MAPS}/${NAME}.${ext}' ]" \
        || die "${PULL}:${REMOTE_MAPS}/${NAME}.${ext} ya existe (usa --force para sobrescribir)"
    done
  fi
  BASE="${REMOTE_MAPS}/${NAME}"
else
  BASE="${LOCAL_BASE}"
  if ! pgrep -f async_slam_toolbox_node >/dev/null 2>&1; then
    echo "AVISO: no hay un slam_toolbox corriendo en esta máquina. Si corre en la Pi, los archivos se" >&2
    echo "       guardarían allí: usa --pull usuario@host (o ejecuta este script en la Pi)." >&2
  fi
fi

SER="${PREFIX}/slam_toolbox/serialize_map"
SAVE="${PREFIX}/slam_toolbox/save_map"
timeout 10 ros2 service list 2>/dev/null | grep -qx "${SER}" \
  || die "no existe el servicio ${SER}: ¿está corriendo mapping.launch.py y el namespace es '${NAMESPACE}'?"

# Llama a un servicio y muestra su respuesta (si falla, enseña el motivo).
call_service() {
  local service="$1" type="$2" request="$3" out
  out="$(timeout 60 ros2 service call "${service}" "${type}" "${request}" 2>&1)" \
    || { echo "${out}" >&2; die "falló la llamada a ${service}"; }
  echo "${out}" | sed -n '/response/,$p' | sed 's/^/      /'
}

echo "[1/2] Guardando pose graph en ${BASE}.posegraph/.data ..."
call_service "${SER}" slam_toolbox/srv/SerializePoseGraph "{filename: '${BASE}'}"

echo "[2/2] Guardando imagen en ${BASE}.yaml/.pgm ..."
call_service "${SAVE}" slam_toolbox/srv/SaveMap "{name: {data: '${BASE}'}}"

if [ -n "${PULL}" ]; then
  missing=0
  for ext in "${EXTS[@]}"; do
    ssh "${PULL}" "[ -s '${BASE}.${ext}' ]" || { echo "ERROR: no se generó ${PULL}:${BASE}.${ext}" >&2; missing=1; }
  done
  [ "${missing}" -eq 0 ] || die "el mapa no se guardó completo en ${PULL}:${REMOTE_MAPS}"
  echo "[+] Copiando de ${PULL} a ${MAPS_DIR} ..."
  for ext in "${EXTS[@]}"; do
    scp -q "${PULL}:${BASE}.${ext}" "${LOCAL_BASE}.${ext}" || die "falló scp de ${BASE}.${ext}"
  done
fi

missing=0
for ext in "${EXTS[@]}"; do
  if [ ! -s "${LOCAL_BASE}.${ext}" ]; then echo "ERROR: no se generó ${LOCAL_BASE}.${ext}" >&2; missing=1; fi
done
if [ "${missing}" -ne 0 ]; then
  [ -n "${PULL}" ] || echo "Los servicios respondieron pero no hay archivos aquí: slam_toolbox corre en otra máquina y los guardó allí." >&2
  [ -n "${PULL}" ] || echo "Repite con --pull usuario@host, o copia los archivos a mano con scp." >&2
  die "el mapa no se guardó completo en ${MAPS_DIR}"
fi

echo
echo "Mapa '${NAME}' guardado en ${MAPS_DIR}:"
ls -l "${LOCAL_BASE}".{posegraph,data,yaml,pgm}
