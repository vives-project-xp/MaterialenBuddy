cmake_minimum_required(VERSION 3.8)
project(hrobot_simulation)

find_package(ament_cmake REQUIRED)

# Launch, configuración del puente y mundos de Gazebo
install(DIRECTORY config launch worlds DESTINATION share/${PROJECT_NAME})

# Nodo Python auxiliar (se lanza con executable='cmd_vel_stamper.py')
install(PROGRAMS scripts/cmd_vel_stamper.py DESTINATION lib/${PROJECT_NAME})

ament_package()
