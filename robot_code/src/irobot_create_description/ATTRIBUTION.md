# Procedencia y licencias

Este paquete mezcla archivos oficiales de iRobot (sin modificar) y archivos propios.

## Archivos oficiales de iRobot (BSD de 3 cláusulas, © 2021 iRobot Corporation)

- **Origen:** <https://github.com/iRobotEducation/create3_sim> (rama `jazzy`),
  carpeta `irobot_create_common/irobot_create_description`.
- **Licencia:** ver el archivo `LICENSE` de este paquete (debe conservarse en cualquier redistribución).
- **Archivos:**
  - `meshes/` (todas las mallas).
  - `urdf/create3.urdf.xacro`, `bumper`, `button`, `caster`, `common_properties`, `wheel`, `wheel_drop`
    y `wheel_with_wheeldrop` (`*.urdf.xacro`).
  - `urdf/dock/` y `urdf/sensors/`, salvo `lidar_ld19.urdf.xacro`.
- **Modificaciones:** ninguna. Si alguna vez se edita un archivo oficial, anotarlo aquí.

## Archivos propios (Apache-2.0)

- `urdf/create3_ld19.urdf.xacro`: une el Create 3 con el LiDAR LD19.
- `urdf/sensors/lidar_ld19.urdf.xacro`: macro del LD19 con los datos del datasheet.
- `launch/display.launch.py` y `rviz/`.
