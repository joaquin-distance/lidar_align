
import numpy as np
import lanelet2
from lanelet2.core import GPSPoint
from lanelet2.projection import UtmProjector
from scipy.spatial.transform import Rotation
from typing import Tuple, Optional
from dataclasses import dataclass
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
import sys # for error handling

try:
    from inertiallabs_msgs.msg import InsData
except ImportError:
    print("Error: inertiallabs_msgs is required. Make sure ROS2 workspace is sourced.")
    sys.exit(1)

from geometry_msgs.msg import TransformStamped

class InsDataConverter:
    """
    Combines INS to TransformStamped conversion and pose extraction functionality.
    """

    def __init__(self):
        self.proj: Optional[UtmProjector] = None
        self.first_message = True

    def ins_to_transform(self, msg: InsData, timestamp: int) -> TransformStamped:
        """
        Convert INS data message to TransformStamped message.

        Parameters
        ----------
        msg : InsData
            INS data message from the bag file.
        timestamp : int
            Nanosecond timestamp.

        Returns
        -------
        TransformStamped
            Converted TransformStamped message.
        """
        # Convert ypr to yaw, pitch, roll (degrees)
        yaw_deg = float(msg.ypr.x)
        pitch_deg = float(msg.ypr.y)
        roll_deg = float(msg.ypr.z)

        # Yaw correction to Standard Clockwise orientation
        yaw_deg_corr = (90 - yaw_deg) % 360

        quats = Rotation.from_euler(
            "zxy", [yaw_deg_corr, pitch_deg, roll_deg], degrees=True
        ).as_quat()

        if self.proj is None:
            self.proj = UtmProjector(
                lanelet2.io.Origin(msg.llh.x, msg.llh.y, msg.llh.z)
            )
            print(f"Projector initialized with {msg.llh.x}, {msg.llh.y}")

        xyz_p = self.proj.forward(GPSPoint(msg.llh.x, msg.llh.y, msg.llh.z))

        # Create TransformStamped message
        transform_msg = TransformStamped()
        transform_msg.header.stamp.sec = timestamp // 1_000_000_000
        transform_msg.header.stamp.nanosec = timestamp % 1_000_000_000
        transform_msg.header.frame_id = "odom"
        transform_msg.child_frame_id = msg.header.frame_id

        # Set translation
        transform_msg.transform.translation.x = float(xyz_p.x)
        transform_msg.transform.translation.y = float(xyz_p.y)
        transform_msg.transform.translation.z = float(xyz_p.z)

        # Set rotation (quaternion: x, y, z, w)
        transform_msg.transform.rotation.x = float(quats[0])
        transform_msg.transform.rotation.y = float(quats[1])
        transform_msg.transform.rotation.z = float(quats[2])
        transform_msg.transform.rotation.w = float(quats[3])

        return transform_msg

    def extract_pose_from_ins_data(self, msg) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts position and quaternion orientation from INS data message.

        Parameters
        ----------
        msg : InsData
            INS data message from the bag file.
        
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Position vector (3,) and orientation quaternion (4,)
        """
        yaw_deg = float(msg.ypr.x)
        pitch_deg = float(msg.ypr.y)
        roll_deg = float(msg.ypr.z)

        if self.first_message:
            self.first_message = False
            print(f"First INS message: LLH = ({msg.llh.x}, {msg.llh.y}, {msg.llh.z})")

        quats = Rotation.from_euler("zxy", [yaw_deg, pitch_deg, roll_deg], degrees=True).as_quat()  # xyzw

        if self.proj is None:
            self.proj = UtmProjector(lanelet2.io.Origin(msg.llh.x, msg.llh.y, msg.llh.z))
            print(f"UTM projector initialized with origin: ({msg.llh.x}, {msg.llh.y})")

        xyz_p = self.proj.forward(GPSPoint(msg.llh.x, msg.llh.y, msg.llh.z))

        p = np.array([float(xyz_p.x), float(xyz_p.y), float(xyz_p.z)], dtype=np.float64)
        q = np.array([float(quats[0]), float(quats[1]), float(quats[2]), float(quats[3])], dtype=np.float64)
        return p, q



def twist_to_T(dp: np.ndarray, rotvec: np.ndarray) -> np.ndarray:
    """Build SE(3) from translation + rotation-vector."""
    Rm = Rotation.from_rotvec(rotvec).as_matrix()
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = Rm
    T[:3, 3] = dp
    return T


def pose_to_T(p: np.ndarray, q_xyzw: np.ndarray) -> np.ndarray:
    Rm = Rotation.from_quat(q_xyzw).as_matrix()
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = Rm
    T[:3, 3] = p
    return T


def T_to_6dof(T: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return (dp(3), drotvec(3)) where drotvec is SO(3) rotation vector (axis*angle), radians.
    """
    dp = T[:3, 3].copy()
    drotvec = Rotation.from_matrix(T[:3, :3]).as_rotvec()  # (3,)
    return dp, drotvec




    
def open_reader(bag_path: str) -> SequentialReader:
    reader = SequentialReader()
    storage_options = StorageOptions(uri=bag_path, storage_id="mcap")
    converter_options = ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr")
    reader.open(storage_options, converter_options)
    return reader