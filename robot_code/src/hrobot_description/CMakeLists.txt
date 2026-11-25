cmake_minimum_required(VERSION 3.8)

# TODO 1: nombre del proyecto (el mismo que en package.xml)
project(hrobot_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf DESTINATION share/${PROJECT_NAME})

ament_package()
