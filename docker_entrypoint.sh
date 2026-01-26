#!/bin/bash
# Copyright 2026 Distance Technologies Oy. For internal use only.
#
set -e

# Source ROS environment
source /opt/ros/noetic/setup.bash

# Change to catkin workspace
cd /root/catkin_ws

# Install dependencies if package.xml exists
if [ -f "src/lidar_align/package.xml" ]; then
    echo "Installing ROS dependencies..."
    apt-get update && rosdep install --from-paths src --ignore-src -r --rosdistro noetic -y || true
fi

# Build the workspace if it hasn't been built
if [ ! -f "devel/setup.bash" ]; then
    echo "Building catkin workspace..."
    catkin_make
fi

# Source the workspace
if [ -f "devel/setup.bash" ]; then
    source devel/setup.bash
    echo "Workspace built and sourced successfully!"
    # Add to bashrc so it's sourced in new shells
    if ! grep -q "source /root/catkin_ws/devel/setup.bash" ~/.bashrc; then
        echo "if [ -f /root/catkin_ws/devel/setup.bash ]; then source /root/catkin_ws/devel/setup.bash; fi" >> ~/.bashrc
    fi
fi

# Execute the command passed to the container
exec "$@"

