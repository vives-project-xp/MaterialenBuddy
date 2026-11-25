cmake_minimum_required(VERSION 3.8)
project(mrobot_bringup)

find_package(ament_cmake REQUIRED)

# Launch files, parameters (slam_params.yaml, nav2_params.yaml) and RViz configurations
install(DIRECTORY config launch rviz DESTINATION share/${PROJECT_NAME})

# Python nodes: installed as executables (launched with executable='odom_relay.py')
install(PROGRAMS
  scripts/odom_relay.py
  scripts/scan_resampler.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
