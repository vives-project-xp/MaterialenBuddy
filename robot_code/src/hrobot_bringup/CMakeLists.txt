cmake_minimum_required(VERSION 3.8)
project(hrobot_bringup)

find_package(ament_cmake REQUIRED)

# Launch files, parámetros (slam_params.yaml; nav2_params.yaml en el paso 4) y configuraciones de RViz
install(DIRECTORY config launch rviz DESTINATION share/${PROJECT_NAME})

# Nodos Python: se instalan como ejecutables (se lanzan con executable='odom_relay.py')
install(PROGRAMS
  scripts/odom_relay.py
  scripts/scan_resampler.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
