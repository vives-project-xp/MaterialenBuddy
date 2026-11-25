# robot_code

Código ROS 2 del robot de MaterialenBuddy: un **iRobot Create 3** con una **Raspberry Pi 5** y un **LiDAR LD19**,
sobre **ROS 2 Jazzy**.

El robot hace tres cosas:

1. **Mapea** un espacio con `slam_toolbox`, moviéndolo por teleoperación.
2. **Navega** de forma autónoma sobre el mapa guardado, con AMCL y Nav2 (las metas se dan desde RViz).
3. Se **simula** antes en Gazebo Harmonic.

> **Estado: nada de esto se ha probado todavía.** El código está escrito y revisado, y los scripts y
> archivos de configuración pasan las comprobaciones de sintaxis, pero no se ha ejecutado con ROS 2, con Gazebo ni con el
> robot. Ver [Primera prueba](#primera-prueba-qué-comprobar).

## Estructura

```text
robot_code/
├── maps/                          mapas guardados (el contenido no se versiona)
├── scripts/
│   ├── setup_pi.sh                prepara la Pi: rosdep, red ROS 2, regla udev. No compila
│   ├── save_map.sh                guarda el mapa que está construyendo slam_toolbox
│   └── rviz_remote.sh             abre RViz en tu PC para el robot que corre en la Pi
└── src/
    ├── irobot_create_description/ URDF del Create 3 (oficial) + LD19 (propio) + launch para verlo en RViz
    ├── hrobot_bringup/            robot real: LiDAR, mapeo y navegación
    ├── hrobot_simulation/         Gazebo Harmonic
    ├── irobot_create_control/     configuración del controlador de ruedas (solo simulación; copia mínima)
    └── ldlidar_stl_ros2/          driver oficial del LD19 (copia, no hace falta clonarlo)
```

El prefijo `hrobot_` viene del proyecto del que se partió; los paquetes de iRobot conservan su nombre original
porque los URDF oficiales lo referencian.

## Cómo encaja

- El **Create 3 corre su propio firmware**: se alcanza por red y vive en el namespace `/r2`
  (`/r2/odom`, `/r2/tf`, `/r2/cmd_vel`...). Este código **no lo arranca**.
- La **Raspberry Pi** corre este workspace: lee el LD19 por USB, publica el modelo del robot y ejecuta `slam_toolbox` o
  Nav2. Pi y Create 3 deben usar el mismo `ROS_DOMAIN_ID` y el mismo RMW.
- **RViz** conviene abrirlo en tu PC (`scripts/rviz_remote.sh`), no en la Pi.

Todo el stack cuelga del namespace del robot (`/r2/scan`, `/r2/map`...). Se cambia con el argumento
`robot_namespace:=` o la variable de entorno `CREATE3_ROBOT_NAMESPACE`. La simulación corre **sin namespace**.

## Requisitos

- Ubuntu con **ROS 2 Jazzy**, `git`, `colcon` y `rosdep`.
- Para la simulación (en un PC): `ros-jazzy-ros-gz`, `ros-jazzy-gz-ros2-control` y `ros-jazzy-ros2-controllers`.

## Instalación en la Raspberry Pi

```bash
cd robot_code
scripts/setup_pi.sh                       # rosdep, ROS_DOMAIN_ID / RMW, regla udev /dev/ldlidar
colcon build --symlink-install --parallel-workers 2 --packages-up-to hrobot_bringup
source install/setup.bash
```

`setup_pi.sh` no compila: el `colcon build` lo lanzas tú. `--packages-up-to` deja fuera la simulación y
`--parallel-workers 2` evita agotar la RAM de la Pi. Opciones del script: `--skip-udev`, `--skip-net`, `--domain-id N`,
`--rmw NOMBRE` (ver `scripts/setup_pi.sh --help`).

Después de `setup_pi.sh`, cierra sesión y vuelve a entrar (grupo `dialout`), y configura el **mismo RMW y dominio en el Create 3**
(su interfaz web, *Application > ROS 2*). Reinicia su aplicación tras cambiarlos. Para comprobar la conexión:

```bash
ros2 topic list | grep -E '/r2/(odom|cmd_vel)'
```

## Uso con el robot real

### 1. Mapear

En la Pi:

```bash
ros2 launch hrobot_bringup mapping.launch.py lidar_port:=/dev/ldlidar rviz:=false
```

En tu PC, para ver el mapa:

```bash
scripts/rviz_remote.sh mapping
```

Mueve el robot con el teclado (la Pi o tu PC):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/r2/cmd_vel
```

Cuando el mapa esté completo, guárdalo (con `mapping.launch.py` todavía corriendo):

```bash
scripts/save_map.sh mapa1                          # en la máquina donde corre slam_toolbox
scripts/save_map.sh mapa1 --pull usuario@host-pi   # si lo ejecutas desde otra máquina
```

Genera en `maps/` cuatro archivos: `mapa1.yaml` y `mapa1.pgm` (la imagen, para navegar) y `mapa1.posegraph` y
`mapa1.data` (el grafo de poses de slam_toolbox). Son archivos locales: no se suben al repositorio.

### 2. Navegar

Pon el robot en el punto desde el que mapeaste (el origen del mapa, normalmente el dock) y, en la Pi:

```bash
ros2 launch hrobot_bringup navigation.launch.py map_yaml:=$PWD/maps/mapa1.yaml lidar_port:=/dev/ldlidar rviz:=false
```

En tu PC: `scripts/rviz_remote.sh navigation`. La meta se da con la herramienta **2D Goal Pose** de RViz.

AMCL arranca en `initial_x/y/yaw` (por defecto `0 0 0`, el origen del mapa). Si el robot está en otro sitio, pasa esos
argumentos o `set_initial_pose:=false` y usa **2D Pose Estimate** en RViz.

### Argumentos útiles

| Argumento | Dónde | Para qué |
|---|---|---|
| `lidar_port` | mapping, navigation | Puerto del LD19 (`/dev/ldlidar` con la regla udev; `/dev/ttyUSB0` sin ella) |
| `laser_scan_dir` | mapping, navigation | Sentido de giro del LD19: cámbialo si el scan sale invertido |
| `laser_yaw` | mapping, navigation | Giro del sensor respecto al frente del robot (rad). Con el sensor real se usó `-1.5707963` |
| `robot_namespace` | todos | Namespace del robot (por defecto `r2`; vacío = ninguno) |
| `rviz` | todos | `false` para no abrir RViz (en la Pi) |
| `map_yaml` | navigation | Ruta absoluta al `.yaml` del mapa (obligatorio) |

## Simulación (en un PC)

```bash
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source install/setup.bash
ros2 launch hrobot_simulation sim.launch.py                              # mapear
ros2 run teleop_twist_keyboard teleop_twist_keyboard                     # en otra terminal
scripts/save_map.sh sala --namespace ''                                  # la simulación no usa namespace
ros2 launch hrobot_simulation sim.launch.py nav:=true map_yaml:=$PWD/maps/sala.yaml
```

Otros argumentos: `headless:=true` (sin interfaz de Gazebo), `x`, `y`, `yaw` (pose inicial) y `world` (otro mundo `.sdf`).
El mundo por defecto es una sala de 8×8 m con un tabique y obstáculos.

## Cosas que no son evidentes

- **`scan_resampler`**: el LD19 real entrega entre ~500 y 504 lecturas por vuelta, y `slam_toolbox` exige un número fijo.
  El nodo publica `scan` con siempre 500 rayos a partir de `scan_raw`. En simulación no hace falta.
- **`odom_relay`**: el Create 3 publica `odom` con QoS *best effort* y Nav2 lo pide *reliable*; el nodo lo republica en
  `odom_reliable`. Solo con el robot real.
- **`cmd_vel_stamper`**: el `diff_drive_controller` de Jazzy recibe `TwistStamped`, pero el teleop y Nav2 publican
  `Twist`. Solo en simulación.
- **`irobot_create_control`**: el URDF oficial lo referencia al usar `gazebo:=ignition`. Solo hace falta en simulación.
- **El modelo de la Pi incluye el URDF completo del Create 3**, no uno mínimo. El Create 3 también publica sus propios frames:
  conviene comprobar que no haya transformaciones duplicadas (`ros2 topic echo /r2/tf_static`).

## Primera prueba: qué comprobar

Puntos donde es más probable que haga falta ajustar algo:

- **Modelo (PC):** `ros2 launch irobot_create_description display.launch.py`. Falta crear `rviz/model.rviz` desde RViz.
- **Compilación del driver del LD19 y puerto serie:** `ls -l /dev/ldlidar`; si no existe, `lsusb` y revisa el identificador de la regla udev.
- **El scan sale girado o invertido:** ajusta `laser_yaw` y `laser_scan_dir`.
- **`slam_toolbox` no se activa:** es un nodo con ciclo de vida; el launch lo configura y activa. Mira `ros2 lifecycle get /r2/slam_toolbox`.
- **Los `.rviz`** están escritos a mano y sin probar: si algo no se ve, ajústalo en RViz y guarda la configuración.
- **Simulación:** que los *spawners* no agoten su tiempo de espera al cargar las mallas, que existan `/odom`, `/tf` y
  `/joint_states`, y que las mallas se encuentren (`GZ_SIM_RESOURCE_PATH`).

## Código de terceros y licencias

| Paquete | Origen | Licencia |
|---|---|---|
| `irobot_create_description` (URDF y mallas oficiales) | [iRobotEducation/create3_sim](https://github.com/iRobotEducation/create3_sim), rama `jazzy` | BSD-3-Clause |
| `irobot_create_control` | ídem (copia mínima) | BSD-3-Clause |
| `ldlidar_stl_ros2` | [ldrobotSensorTeam/ldlidar_stl_ros2](https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2) (con una modificación) | MIT |

El detalle de qué se copió y qué se modificó está en `VENDORED.md` (`ldlidar_stl_ros2`, `irobot_create_control`) y en
`ATTRIBUTION.md` (`irobot_create_description`). El código propio del proyecto es Apache-2.0.
