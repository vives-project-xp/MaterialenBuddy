# Código de terceros incluido en el repositorio

Este paquete es una copia del driver oficial del LiDAR LD19 / LD06 / STL27L de LDRobot.
Se incluye aquí para no tener que clonarlo aparte al preparar el robot.

- **Origen:** <https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2> (rama `master`)
- **Commit copiado:** `bf668a89baf722a787dadc442860dcbf33a82f5a`
- **Licencia:** MIT, © 2020 SHENZHEN LDROBOT CO., LTD. (ver `LICENSE`; debe conservarse)
- **Se excluyó:** la carpeta `.git` y el `.gitignore` del original.
- **Se eliminó, por no ser necesario:** `launch/` (launch de ejemplo del fabricante; el nuestro está en
  `hrobot_bringup`), `rviz2/`, `scripts/` (reglas udev de ejemplo; las gestiona `scripts/setup_pi.sh`
  del proyecto) y `README.md`. Se conserva todo el código del driver, incluido el soporte de LD06 y STL27L.

## Modificaciones respecto al original

1. `ldlidar_driver/include/logger/log_module.h`: se descomentó `#include <pthread.h>`.
   Sin él, `pthread_mutex_t` queda sin declarar y la compilación falla con el GCC de Ubuntu 24.04.
2. `CMakeLists.txt`: se quitó `install(DIRECTORY launch rviz2 ...)`, porque esas carpetas ya no existen.

Cualquier otro cambio en este paquete debe anotarse aquí.
