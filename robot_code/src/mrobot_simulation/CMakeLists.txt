cmake_minimum_required(VERSION 3.8)
project(mrobot_simulation)

find_package(ament_cmake REQUIRED)

# Launch files, bridge configuration and Gazebo worlds
install(DIRECTORY config launch worlds DESTINATION share/${PROJECT_NAME})

# Helper Python node (launched with executable='cmd_vel_stamper.py')
install(PROGRAMS scripts/cmd_vel_stamper.py DESTINATION lib/${PROJECT_NAME})

ament_package()
