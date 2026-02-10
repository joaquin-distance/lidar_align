# Copyright 2026 Distance Technologies Oy. For internal use only.
#
# One-time setup: creates a minimal ROS2 workspace with inertiallabs-ros2-pkgs
# so the bag_converter can resolve InertialLabs/InsData message types.
# No need to reorganize the repo; lidar_align stays as-is (ROS1 in its own workspace).
#
# Usage (from repo root):
#   ./scripts/setup_ros2_deps.sh
# Then before running bag_converter:
#   source ros2_deps/install/setup.bash

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS2_DEPS_WS="$REPO_ROOT/ros2_deps"
REPOS_FILE="$REPO_ROOT/workspace.repos"

if [ ! -f "$REPOS_FILE" ]; then
  echo "Error: workspace.repos not found at $REPOS_FILE"
  exit 1
fi

# vcstool is required
if ! command -v vcs >/dev/null 2>&1; then
  echo "vcstool not found. Install with: pip install vcstool"
  exit 1
fi

mkdir -p "$ROS2_DEPS_WS/src"
cd "$ROS2_DEPS_WS"
vcs import src < "$REPOS_FILE"

echo "Building ROS2 deps workspace..."
if command -v colcon >/dev/null 2>&1; then
  colcon build
else
  echo "colcon not found. Source ROS2 first, e.g.: source /opt/ros/humble/setup.bash"
  exit 1
fi

echo ""
echo "Done. Before running bag_converter, run:"
echo "  source $ROS2_DEPS_WS/install/setup.bash"
echo "Then run preprocess_bag.py from the repo root as usual."
