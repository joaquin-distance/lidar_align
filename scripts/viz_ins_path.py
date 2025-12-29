# Copyright 2026 Distance Technologies Oy. For internal use only.
#

import argparse
from matplotlib import pyplot as plt
from utils import InsDataConverter, pose_to_T, open_reader
from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import deserialize_message
import numpy as np

def plot_paths_side_by_side(pose_path):
    """Plot 3D and 2D trajectories side by side in a single figure."""

    fig = plt.figure(figsize=(18, 8))

    # Left: 3D trajectory
    ax3d = fig.add_subplot(1, 2, 1, projection='3d')
    ax3d.plot(
        pose_path[:, 0, -1],
        pose_path[:, 1, -1],
        pose_path[:, 2, -1],
        'r-',
        label="Pose Trajectory"
    )
    # Start marker
    ax3d.scatter(
        pose_path[0, 0, -1],
        pose_path[0, 1, -1],
        pose_path[0, 2, -1],
        c='g',
        marker='o',
        s=100,
        label='Start'
    )
    # End marker
    ax3d.scatter(
        pose_path[-1, 0, -1],
        pose_path[-1, 1, -1],
        pose_path[-1, 2, -1],
        c='b',
        marker='o',
        s=100,
        label='End'
    )
    ax3d.set_xlabel('X')
    ax3d.set_ylabel('Y')
    ax3d.set_zlabel('Z')
    ax3d.legend()
    ax3d.set_title("3D Pose Trajectory")

    # Right: 2D trajectory (XY)
    ax2d = fig.add_subplot(1, 2, 2)
    ax2d.plot(
        pose_path[:, 0, -1],
        pose_path[:, 1, -1],
        'r-',
        label="Pose 2D Trajectory (XY)"
    )
    ax2d.scatter(
        pose_path[0, 0, -1],
        pose_path[0, 1, -1],
        c='g',
        marker='o',
        s=100,
        label='Start'
    )
    ax2d.scatter(
        pose_path[-1, 0, -1],
        pose_path[-1, 1, -1],
        c='b',
        marker='o',
        s=100,
        label='End'
    )
    ax2d.set_xlabel('X')
    ax2d.set_ylabel('Y')
    ax2d.legend()
    ax2d.axis('equal')
    ax2d.set_title("2D Pose Trajectory (XY)")
    plt.tight_layout()
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Visualize INS trajectory from ROS2 bag")
    parser.add_argument("bag_path", type=str, help="Path to input ROS2 bag")
    args = parser.parse_args()

    bag_path = args.bag_path
    reader = open_reader(bag_path)
    ins_msg_cls = get_message("inertiallabs_msgs/msg/InsData")
    ins_extractor = InsDataConverter()
    poses_ins = []

    while reader.has_next():
        topic, data, time_stamp = reader.read_next()
        if "ins_data" in topic:
            msg = deserialize_message(data, ins_msg_cls)
            p, q = ins_extractor.extract_pose_from_ins_data(msg)
            pose = pose_to_T(p, q)
            poses_ins.append(pose)
    poses_ins = np.array(poses_ins)
    if poses_ins.size == 0:
        print("No INS poses found in the bag.")
        return
    print(f"Loaded {poses_ins.shape[0]} poses from {bag_path}")

    plot_paths_side_by_side(poses_ins)

if __name__ == "__main__":
    main()