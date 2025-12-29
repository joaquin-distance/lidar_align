# Copyright 2025 Distance Technologies Oy. For internal use only.
#
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------------------
# Basic packages
# --------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    curl \
    ca-certificates \
    software-properties-common \
    lsb-release \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------
# Install Kitware CMake 3.27.9 (cmake >= 3.14 required)
# --------------------------------------------------------------
RUN wget https://github.com/Kitware/CMake/releases/download/v3.27.9/cmake-3.27.9-linux-x86_64.tar.gz -O /tmp/cmake.tar.gz && \
    mkdir -p /opt/cmake && \
    tar -xzf /tmp/cmake.tar.gz -C /opt/cmake --strip-components=1 && \
    ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake && \
    ln -s /opt/cmake/bin/ctest /usr/local/bin/ctest && \
    ln -s /opt/cmake/bin/cpack /usr/local/bin/cpack && \
    rm /tmp/cmake.tar.gz

# Verify CMake installation
RUN cmake --version

# --------------------------------------------------------------
# Install GCC >= 7.5 (Ubuntu 20.04 default is GCC 9, which satisfies requirement)
# --------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    gcc-9 \
    g++-9 \
    && rm -rf /var/lib/apt/lists/*

# Update alternatives to use gcc-9
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 100 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 100

# Verify GCC version
RUN gcc --version && g++ --version

# --------------------------------------------------------------
# Install ROS Noetic Desktop
# --------------------------------------------------------------
RUN sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list' && \
    apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654 && \
    apt-get update && apt-get install -y \
    ros-noetic-desktop-full \
    && rm -rf /var/lib/apt/lists/*

# Initialize ROS environment
RUN echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc

# --------------------------------------------------------------
# Install rosdep and initialize
# --------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    libnlopt-dev \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

RUN sudo rosdep init || true && \
    rosdep update --include-eol-distros



# --------------------------------------------------------------
# Setup catkin workspace and clone lidar_align
# --------------------------------------------------------------
RUN mkdir -p ~/catkin_ws/src && \
    cd ~/catkin_ws/src && \
    cd ~/catkin_ws

WORKDIR /root/catkin_ws

CMD ["/bin/bash"]
