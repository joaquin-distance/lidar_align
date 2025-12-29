cmake_minimum_required(VERSION 2.8.3)
project(lidar_align)

add_definitions(-std=c++17 -Ofast)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  image_transport
  cv_bridge
  pcl_ros
  rosbag
  sensor_msgs
  geometry_msgs
)

# NLOPT is frustratingly inconsistent in the name of its cmake file so we use our own
# Include the custom NLOPT config file directly from the package directory
include(${CMAKE_CURRENT_SOURCE_DIR}/NLOPTConfig.cmake)
if(NOT NLOPT_FOUND)
    message(FATAL_ERROR "NLOPT not found. Please ensure libnlopt-dev is installed.")
endif()

# Search for the C++ header (nlopt.hpp) - it might be in a different location than nlopt.h
find_path(NLOPT_CPP_HEADER_DIR
  NAMES nlopt.hpp
  PATHS ${NLOPT_INCLUDE_DIRS}
        /usr/include
        /usr/local/include
  PATH_SUFFIXES nlopt include
  NO_DEFAULT_PATH
)

# If not found, try with default paths
if(NOT NLOPT_CPP_HEADER_DIR)
    find_path(NLOPT_CPP_HEADER_DIR NAMES nlopt.hpp)
endif()

# Try to find via Python package (since pip3 install nlopt was run in Dockerfile)
if(NOT NLOPT_CPP_HEADER_DIR)
    execute_process(
        COMMAND python3 -c "import nlopt; import os; print(os.path.dirname(nlopt.__file__))"
        OUTPUT_VARIABLE NLOPT_PYTHON_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if(NLOPT_PYTHON_DIR AND EXISTS "${NLOPT_PYTHON_DIR}/nlopt.hpp")
        set(NLOPT_CPP_HEADER_DIR ${NLOPT_PYTHON_DIR})
    endif()
endif()

# Also check common Python site-packages locations
if(NOT NLOPT_CPP_HEADER_DIR)
    file(GLOB PYTHON_SITE_PACKAGES "/usr/local/lib/python3*/dist-packages/nlopt")
    file(GLOB PYTHON_SITE_PACKAGES2 "/usr/lib/python3*/dist-packages/nlopt")
    foreach(pkg_dir ${PYTHON_SITE_PACKAGES} ${PYTHON_SITE_PACKAGES2})
        if(EXISTS "${pkg_dir}/nlopt.hpp")
            set(NLOPT_CPP_HEADER_DIR ${pkg_dir})
            break()
        endif()
    endforeach()
endif()

if(NLOPT_CPP_HEADER_DIR)
    # Use the directory where nlopt.hpp was found
    set(NLOPT_INCLUDE_DIRS ${NLOPT_CPP_HEADER_DIR})
    message(STATUS "Found nlopt.hpp in ${NLOPT_CPP_HEADER_DIR}")
else()
    # nlopt.hpp not found - try to download it to a temporary location
    message(STATUS "nlopt.hpp not found in system. Attempting to download...")
    set(NLOPT_HPP_DOWNLOAD_DIR "${CMAKE_CURRENT_BINARY_DIR}/nlopt_include")
    set(NLOPT_HPP_PATH "${NLOPT_HPP_DOWNLOAD_DIR}/nlopt.hpp")
    
    # Create directory if it doesn't exist
    if(NOT EXISTS "${NLOPT_HPP_DOWNLOAD_DIR}")
        file(MAKE_DIRECTORY "${NLOPT_HPP_DOWNLOAD_DIR}")
    endif()
    
    # Download nlopt.hpp if it doesn't exist
    if(NOT EXISTS "${NLOPT_HPP_PATH}")
        message(STATUS "Downloading nlopt.hpp from GitHub...")
        file(DOWNLOAD 
            "https://raw.githubusercontent.com/stevengj/nlopt/master/src/nlopt.hpp"
            "${NLOPT_HPP_PATH}"
            TIMEOUT 30
            STATUS DOWNLOAD_STATUS
        )
        list(GET DOWNLOAD_STATUS 0 STATUS_CODE)
        if(NOT STATUS_CODE EQUAL 0)
            file(REMOVE "${NLOPT_HPP_PATH}")
            message(FATAL_ERROR "Failed to download nlopt.hpp. "
                                "Please download it manually from:\n"
                                "  https://raw.githubusercontent.com/stevengj/nlopt/master/src/nlopt.hpp\n"
                                "And place it in: ${NLOPT_HPP_DOWNLOAD_DIR}/")
        endif()
    endif()
    
    # Verify the downloaded file exists
    if(EXISTS "${NLOPT_HPP_PATH}")
        set(NLOPT_INCLUDE_DIRS "${NLOPT_HPP_DOWNLOAD_DIR}")
        message(STATUS "Using downloaded nlopt.hpp from ${NLOPT_HPP_PATH}")
    else()
        message(FATAL_ERROR "nlopt.hpp not found and download failed. "
                            "Please download it manually from:\n"
                            "  https://raw.githubusercontent.com/stevengj/nlopt/master/src/nlopt.hpp\n"
                            "And place it in: ${NLOPT_HPP_DOWNLOAD_DIR}/")
    endif()
endif()

include_directories(
  include
  ${NLOPT_INCLUDE_DIRS}
  ${catkin_INCLUDE_DIRS}
)

add_library(${PROJECT_NAME}
  src/sensors.cpp
  src/aligner.cpp  
  src/loader.cpp
)
target_link_libraries(${PROJECT_NAME} ${catkin_LIBRARIES} ${NLOPT_LIBRARIES})

catkin_package(
   INCLUDE_DIRS include/
   LIBRARIES ${PROJECT_NAME}
)

add_executable(lidar_align_node
  src/lidar_align_node.cpp
  
)
target_link_libraries(lidar_align_node ${PROJECT_NAME} ${catkin_LIBRARIES})

install(DIRECTORY include/lidar_align
  DESTINATION include
  FILES_MATCHING 
    PATTERN "*.h"
    PATTERN "*.hpp"
)
