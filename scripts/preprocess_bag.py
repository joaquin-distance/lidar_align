# Copyright 2025 Distance Technologies Oy. For internal use only.
#

"""
This script reads a ROS2 bag file, downsamples pointcloud messages to a specified
frequency (default 10 Hz), converts InertialLabs/InsData messages to 
geometry_msgs/TransformStamped, and converts the result to ROS1 Noetic format.
The output bag file can be used to calibrate the lidar using the lidar_align package.

Usage:
python scripts/preprocess_bag.py /path/to/your/ros2bag/ --output /path/to/your/ros1bag.bag

Options:
  --hz : Target frequency in Hz for pointcloud messages (default: 10.0)
  --output : Path to the output ROS1 bag file (.bag)
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Set
from utils import InsDataConverter

try:
    import rosbag2_py
except ImportError:
    print("Error: rosbag2_py is required. Install with: pip install rosbag2_py")
    sys.exit(1)

from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.utilities import get_message

def get_pointcloud_topics(topic_types: list) -> Set[str]:
    """
    Identify pointcloud topics from the bag file.

    Parameters
    ----------
    topic_types : list
        List of TopicMetadata objects from the bag file.

    Returns
    -------
    Set[str]
        Set of topic names that are pointcloud topics.
    """
    pointcloud_topics = set()
    for topic in topic_types:
        if "PointCloud2" in topic.type:
            pointcloud_topics.add(topic.name)
    return pointcloud_topics



def downsample_bag(
    input_bag_path: str,
    output_bag_path: str,
    target_hz: float = 15.0,
) -> list:
    """
    Downsample pointcloud messages in a ROS2 bag file.

    Parameters
    ----------
    input_bag_path : str
        Path to the input ROS2 bag file.
    output_bag_path : str
        Path to the output ROS2 bag file.
    target_hz : float
        Target frequency in Hz for pointcloud messages (default: 10.0).

    Returns
    -------
    list
        List of topic names in the output bag.
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_bag_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate minimum time interval between messages (in nanoseconds)
    min_interval_ns = int(1_000_000_000 / target_hz)

    # Create reader - try different storage formats
    reader = rosbag2_py.SequentialReader()
    storage_ids = ["sqlite3", "mcap"]
    reader_opened = False

    for storage_id in storage_ids:
        try:
            storage_options = rosbag2_py.StorageOptions(
                uri=input_bag_path, storage_id=storage_id
            )
            converter_options = rosbag2_py.ConverterOptions(
                input_serialization_format="cdr",
                output_serialization_format="cdr",
            )
            reader.open(storage_options, converter_options)
            reader_opened = True
            print(f"Opened input bag file with storage format: {storage_id}")
            break
        except Exception as e:
            print(f"Failed to open with {storage_id}: {e}")
            continue

    if not reader_opened:
        print(f"Error: Could not open bag file {input_bag_path}")
        return []

    # Get topic types
    topic_types = reader.get_all_topics_and_types()
    type_map = {topic.name: topic.type for topic in topic_types}
    pointcloud_topics = get_pointcloud_topics(topic_types)
    ins_topic = "/Inertial_Labs/ins_data"

    print(f"Found {len(pointcloud_topics)} pointcloud topic(s): {pointcloud_topics}")
    if ins_topic:
        print(f"Found InsData topic: {ins_topic}")
    else:
        print("Warning: No InsData topic found in bag file")
    print(f"Total topics in bag: {len(topic_types)}")

    # Create writer
    writer = rosbag2_py.SequentialWriter()
    storage_options = rosbag2_py.StorageOptions(
        uri=output_bag_path, storage_id="mcap"
    )
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format="cdr",
        output_serialization_format="cdr",
    )
    writer.open(storage_options, converter_options)

    # Initialize converter
    ins_converter = InsDataConverter()

    # Register only the topics we want in the output bag
    topic_id = 0
    output_topics = {}

    # Register pointcloud topics
    for pc_topic in pointcloud_topics:
        writer.create_topic(
            rosbag2_py.TopicMetadata(
                id=topic_id,
                name=pc_topic,
                type=type_map[pc_topic],
                serialization_format="cdr",
            )
        )
        output_topics[pc_topic] = topic_id
        topic_id += 1

    # Register tf topic (for TransformStamped messages)
    tf_topic = "/tf"
    writer.create_topic(
        rosbag2_py.TopicMetadata(
            id=topic_id,
            name=tf_topic,
            type="geometry_msgs/msg/TransformStamped",
            serialization_format="cdr",
        )
    )
    output_topics[tf_topic] = topic_id

    print(f"\nOutput bag will contain:")
    print(f"  - Pointcloud topics: {list(pointcloud_topics)}")
    print(f"  - TF topic: {tf_topic}")

    # Track last write time for each pointcloud topic
    last_write_time: Dict[str, int] = {topic: 0 for topic in pointcloud_topics}

    # Statistics
    total_messages = 0
    pointcloud_messages = 0
    pointcloud_written = 0
    ins_messages = 0
    tf_messages_written = 0

    print(f"\nProcessing messages...")
    print(f"Target frequency: {target_hz} Hz (min interval: {min_interval_ns / 1e9:.3f} s)")

    # Get message type for InsData if topic exists
    ins_msg_type = None
    if ins_topic and ins_topic in type_map:
        try:
            ins_msg_type = get_message(type_map[ins_topic])
        except Exception as e:
            print(f"Warning: Could not get message type for {ins_topic}: {e}")

    # Get message type for PointCloud2
    pc_msg_type = get_message("sensor_msgs/msg/PointCloud2")

    # Process all messages
    while reader.has_next():
        (topic, data, timestamp) = reader.read_next()
        total_messages += 1

        # Handle pointcloud topics - downsample them
        if topic in pointcloud_topics:
            pointcloud_messages += 1
            # Check if enough time has passed since last write
            if timestamp - last_write_time[topic] >= min_interval_ns:
                # Update pointcloud header timestamp to match bag timestamp
                if pc_msg_type is not None:
                    try:
                        pc_msg = deserialize_message(data, pc_msg_type)
                        # Convert bag timestamp (nanoseconds) to ROS2 Time format
                        pc_msg.header.stamp.sec = timestamp // 1_000_000_000
                        pc_msg.header.stamp.nanosec = timestamp % 1_000_000_000
                        # Serialize the updated message
                        data = serialize_message(pc_msg)
                    except Exception as e:
                        print(f"Warning: Error updating pointcloud timestamp: {e}")
                writer.write(topic, data, timestamp)
                last_write_time[topic] = timestamp
                pointcloud_written += 1
            continue

        # Handle InsData topic - convert to TransformStamped
        if ins_topic and topic == ins_topic and ins_msg_type is not None:
            try:
                ins_msg = deserialize_message(data, ins_msg_type)
                transform_msg = ins_converter.ins_to_transform(ins_msg,timestamp)
                
                # Serialize the TransformStamped message
                tf_data = serialize_message(transform_msg)
                writer.write("/tf", tf_data, timestamp)
                ins_messages += 1
                tf_messages_written += 1
            except Exception as e:
                print(f"Warning: Error converting InsData message: {e}")
            continue

        # Skip all other topics (we only want pointcloud and tf)

        # Progress indicator
        if total_messages % 1000 == 0:
            print(f"Processed {total_messages} messages...", end="\r")

    reader.close()
    writer.close()

    print(f"\n\nROS2 bag processing complete!")
    print(f"Total messages processed: {total_messages}")
    print(f"Pointcloud messages: {pointcloud_messages} (written: {pointcloud_written})")
    print(f"InsData messages: {ins_messages} (converted to tf: {tf_messages_written})")
    print(f"Intermediate ROS2 bag file: {output_bag_path}")
    
    # Return list of topics in the output bag
    output_topics_list = list(pointcloud_topics) + ["/tf"]
    return output_topics_list


def convert_to_ros1(
    ros2_bag_path: str,
    ros1_bag_path: str,
    topics: list,
) -> bool:
    """
    Convert ROS2 bag to ROS1 Noetic format using rosbags-convert.

    Parameters
    ----------
    ros2_bag_path : str
        Path to the ROS2 bag file.
    ros1_bag_path : str
        Path to the output ROS1 bag file.
    topics : list
        List of topics to include in the conversion.

    Returns
    -------
    bool
        True if conversion succeeded, False otherwise.
    """
    # Build the rosbags-convert command
    cmd = [
        "rosbags-convert",
        "--src", ros2_bag_path,
        "--src-typestore", "ros2_kilted",
        "--dst-typestore", "ros1_noetic",
        "--dst", ros1_bag_path,
    ]
    # Add include-topic flags for each topic
    for topic in topics:
        cmd.extend(["--include-topic", topic])

    print(f"\nConverting ROS2 bag to ROS1 Noetic format...")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print("Conversion successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: rosbags-convert failed with return code {e.returncode}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: rosbags-convert not found. Please install rosbags:")
        print("  pip install rosbags")
        return False


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Preprocess ROS2 bag: downsample pointclouds, convert InsData to tf, and convert to ROS1 Noetic"
    )
    parser.add_argument(
        "bag_file",
        type=str,
        help="Path to the input ROS2 bag file",
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=10.0,
        help="Target frequency in Hz for pointcloud messages (default: 10.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to the output ROS1 bag file (.bag)",
    )

    args = parser.parse_args()

    # Validate input bag file exists
    if not Path(args.bag_file).exists():
        print(f"Error: Input bag file does not exist: {args.bag_file}")
        sys.exit(1)

    # Validate hz is positive
    if args.hz <= 0:
        print(f"Error: Hz must be positive, got {args.hz}")
        sys.exit(1)

    # Ensure output path ends with .bag
    output_path = Path(args.output)
    if output_path.suffix != ".bag":
        print(f"Warning: Output path should end with .bag, got {output_path.suffix}")
        output_path = output_path.with_suffix(".bag")

    print(f"Input bag file: {args.bag_file}")
    print(f"Output ROS1 bag file: {output_path}")
    print(f"Target frequency: {args.hz} Hz")

    # Create temporary directory for intermediate ROS2 bag
    with tempfile.TemporaryDirectory(prefix="preprocess_bag_") as tmp_dir:
        tmp_bag_path = Path(tmp_dir) / "downsampled_ros2_bag"
        
        print(f"\nStep 1: Downsampling pointclouds and converting InsData to tf...")
        print(f"Intermediate ROS2 bag will be stored in: {tmp_bag_path}")
        
        # Step 1: Downsample and convert InsData to tf
        topics_to_include = downsample_bag(args.bag_file, str(tmp_bag_path), args.hz)
        
        if not topics_to_include:
            print("Error: Failed to process bag file")
            sys.exit(1)
        
        # Step 2: Convert ROS2 bag to ROS1 Noetic
        print(f"\nStep 2: Converting to ROS1 Noetic format...")
        success = convert_to_ros1(
            str(tmp_bag_path),
            str(output_path),
            topics_to_include,
        )
        
        if not success:
            print("Error: Failed to convert bag to ROS1 format")
            sys.exit(1)
        
        print(f"\n✓ Successfully created ROS1 Noetic bag: {output_path}")
        print(f"  Topics included: {topics_to_include}")


if __name__ == "__main__":
    main()

