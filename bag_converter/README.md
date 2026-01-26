# Bag Converter

This folder contains scripts for converting ROS2 bag files to ROS1 Noetic format for use with the lidar_align package.

## Prerequisites

### System Dependencies

The following system packages are required:

1. **ROS2** - Make sure you have ROS2 installed and your workspace sourced:
   ```bash
   source /opt/ros/<ros2-distro>/setup.bash
   ```

2. **Lanelet2** - Required for GPS coordinate projection:
   ```bash
   sudo apt install ros-<ros2-distro>-lanelet2
   ```
   Replace `<ros2-distro>` with your ROS2 distribution (e.g., `humble`, `iron`, `jazzy`).

   For example, if using ROS2 Humble:
   ```bash
   sudo apt install ros-humble-lanelet2
   ```

### Python Dependencies

Install the required Python packages:

```bash
pip install rosbag2_py rosbags numpy scipy
```

**Note:** Make sure your ROS2 workspace is sourced before running the script, as it needs access to ROS2 message types.

## Usage

The `preprocess_bag.py` script reads a ROS2 bag file, downsamples pointcloud messages, converts InertialLabs/InsData messages to geometry_msgs/TransformStamped, and converts the result to ROS1 Noetic format.

```bash
python bag_converter/preprocess_bag.py /path/to/your/ros2bag/ --output /path/to/your/ros1bag.bag
```

### Options

- `--hz`: Target frequency in Hz for pointcloud messages (default: 10.0)
- `--output`: Path to the output ROS1 bag file (.bag) - **required**

### Example

```bash
python bag_converter/preprocess_bag.py calib_data/calib_helsinki_20_ins_0.mcap --output calib_helsinki_20_ins.bag --hz 10.0
```

## Requirements

Your ROS2 bag file must contain:
- **INS data** on topic `/Inertial_Labs/ins_data` (InertialLabs/InsData messages)
- **Pointcloud data** (sensor_msgs/PointCloud2 messages)

The script will automatically:
1. Downsample pointcloud messages to the specified frequency
2. Convert InsData messages to `geometry_msgs/TransformStamped` messages on `/tf` topic
3. Convert the processed ROS2 bag to ROS1 Noetic format

## Troubleshooting

- **Import errors**: Make sure ROS2 is sourced and lanelet2 is installed
- **Message type errors**: Ensure your ROS2 workspace is sourced and contains the required message definitions
- **Conversion errors**: Verify that `rosbags` package is installed: `pip install rosbags`

