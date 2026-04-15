cmake_minimum_required(VERSION 3.8)
project(minirov_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/VehicleState.msg"
  "msg/VehicleCommand.msg"
  DEPENDENCIES builtin_interfaces
)

ament_package()
