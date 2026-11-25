cmake_minimum_required(VERSION 3.5)

project(irobot_create_control)

find_package(ament_cmake REQUIRED)

# Solo la configuración: el URDF oficial la referencia con $(find irobot_create_control)/config/control.yaml
install(
  DIRECTORY
    config
  DESTINATION
    share/${PROJECT_NAME}/
)

ament_package()
