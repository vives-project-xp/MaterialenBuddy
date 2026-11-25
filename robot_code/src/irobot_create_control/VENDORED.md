# Código de terceros incluido en el repositorio

Copia mínima del paquete `irobot_create_control` del simulador oficial del iRobot Create 3.
Los URDF oficiales de `irobot_create_description` lo referencian (`$(find irobot_create_control)/config/control.yaml`)
para configurar el controlador de las ruedas en Gazebo.

- **Origen:** <https://github.com/iRobotEducation/create3_sim> (rama `jazzy`),
  carpeta `irobot_create_common/irobot_create_control`
- **Commit copiado:** `6c305843afcfe094bf8eb2a0c6997f531e526b9d`
- **Licencia:** BSD de 3 cláusulas, © 2021 iRobot Corporation (ver `LICENSE`; debe conservarse)
- **Se copió:** `config/control.yaml` (sin cambios), `package.xml` y `LICENSE`.

## Modificaciones respecto al original

1. `CMakeLists.txt`: solo instala `config` (se quitó `launch`, porque no se copió) y se eliminaron los tests.
2. `package.xml`: se quitaron las dependencias `ros2launch` y `rsl` y las de tests, que solo usaba la carpeta `launch`.
3. No se copió `launch/include/control.py`: el arranque de los controladores está en
   `hrobot_simulation/launch/sim.launch.py`.

## Aviso: parámetros obsoletos en control.yaml

El YAML está escrito para una versión anterior del `diff_drive_controller`. En Jazzy ya no existen
`use_stamped_vel`, `publish_cmd`, `publish_wheel_data` ni `preserve_turning_radius`: ROS los ignora.
Lo que sí importa en Jazzy: el controlador recibe `TwistStamped` en `diffdrive_controller/cmd_vel`
(por eso la simulación incluye `cmd_vel_stamper.py`).
