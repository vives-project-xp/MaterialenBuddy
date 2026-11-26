"""LiDAR profiles (config/lidars/<model>.yaml), shared by the launch files.

The model is chosen with the lidar_model argument; its default is the LIDAR_MODEL environment variable or 'ld19'.
"""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def lidar_model_argument():
    return DeclareLaunchArgument(
        "lidar_model",
        default_value=EnvironmentVariable("LIDAR_MODEL", default_value="ld19"),
        description="LiDAR profile in config/lidars (env LIDAR_MODEL or 'ld19').",
    )


def load_lidar_profile(context):
    """Return (model, profile dict) for the lidar_model launch argument."""
    model = LaunchConfiguration("lidar_model").perform(context).strip()
    folder = os.path.join(get_package_share_directory("mrobot_bringup"), "config", "lidars")
    path = os.path.join(folder, f"{model}.yaml")
    if not os.path.isfile(path):
        available = sorted(f[:-5] for f in os.listdir(folder) if f.endswith(".yaml"))
        raise RuntimeError(f"Unknown lidar_model:='{model}'. Available: {', '.join(available)}")
    with open(path, encoding="utf-8") as f:
        return model, yaml.safe_load(f)
