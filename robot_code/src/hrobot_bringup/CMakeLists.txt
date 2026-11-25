cmake_minimum_required(VERSION 3.8)
project(hrobot_bringup)

find_package(ament_cmake REQUIRED)

# Launch files (config/ se añade en el paso 3, cuando existan slam_params.yaml y nav2_params.yaml)
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

# Nodos Python: se instalan como ejecutables (se lanzan con executable='odom_relay.py')
install(PROGRAMS
  scripts/odom_relay.py
  scripts/scan_resampler.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
