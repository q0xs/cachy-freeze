cmake_minimum_required(VERSION 3.24)
project(cachy-workstation-idle-agent VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.6 REQUIRED COMPONENTS Gui)
find_package(KF6IdleTime 6.0 REQUIRED)

add_executable(cachy-workstation-idle-agent idle-agent.cpp)
target_compile_options(cachy-workstation-idle-agent PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(cachy-workstation-idle-agent PRIVATE Qt6::Gui KF6::IdleTime)
