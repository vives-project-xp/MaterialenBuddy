#!/usr/bin/env python3
"""Resample sensor_msgs/LaserScan to a FIXED number of beams.

The real LD19 delivers between ~500 and 504 readings per revolution (it varies). slam_toolbox (Karto) fixes the
size with the first scan and warns "LaserRangeScan contains N range readings, expected M" for any other.
This node reads `scan_raw` (driver) and publishes `scan` with ALWAYS `num_beams` beams and the same angles.
It uses the nearest neighbour (no interpolation, so it does not invent distances at obstacle edges).
Real robot only: the simulated Gazebo sensor already delivers a fixed number of beams.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

TWO_PI = 2.0 * math.pi


def resample_arrays(ranges, intensities, angle_min, angle_increment, num_beams):
    """Return (ranges, intensities) with `num_beams` beams spread over 0..2*pi.

    Output beam k points at angle k * (2*pi / num_beams). For each one, the INPUT reading nearest to that
    angle is taken. If the input scan does not cover a full revolution, the beams outside its range are
    left at inf (no reading).
    `intensities` can be None or have a different length than `ranges`: in that case the output has no
    intensities (None is returned in their place).
    Pure Python: ~500 beams at 10 Hz do not justify depending on numpy.
    """
    n_in = len(ranges)
    out_inc = TWO_PI / num_beams
    # The input covers the full revolution if its beams add up to 2*pi (with a tolerance of one and a half beams).
    full_circle = n_in * angle_increment >= TWO_PI - 1.5 * angle_increment
    use_intensities = intensities is not None and len(intensities) == n_in

    ranges_out = []
    intensities_out = [] if use_intensities else None
    for k in range(num_beams):
        # Angle of beam k relative to the start of the input scan, in [0, 2*pi).
        phi = (k * out_inc - angle_min) % TWO_PI
        i = int(round(phi / angle_increment))
        if i >= n_in:
            if full_circle:
                i -= n_in  # the circle closes
            else:
                ranges_out.append(math.inf)
                if use_intensities:
                    intensities_out.append(0.0)
                continue
        ranges_out.append(float(ranges[i]))
        if use_intensities:
            intensities_out.append(float(intensities[i]))
    return ranges_out, intensities_out


class ScanResampler(Node):
    def __init__(self):
        super().__init__("scan_resampler")

        self.declare_parameter("input_topic", "scan_raw")
        self.declare_parameter("output_topic", "scan")
        # 500 = nominal LD19 resolution and what the Gazebo sensor generates (real robot and simulation match).
        self.declare_parameter("num_beams", 500)
        self._n = int(self.get_parameter("num_beams").value)
        if self._n < 2:
            raise ValueError("num_beams debe ser >= 2")

        # RELIABLE matches RELIABLE subscribers (Nav2) and BEST_EFFORT ones (slam_toolbox, RViz).
        output_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE)
        self._pub = self.create_publisher(
            LaserScan, self.get_parameter("output_topic").value, output_qos
        )
        # Sensor-data (BEST_EFFORT) matches a RELIABLE or BEST_EFFORT driver.
        self.create_subscription(
            LaserScan,
            self.get_parameter("input_topic").value,
            self._on_scan,
            qos_profile_sensor_data,
        )

    def _on_scan(self, msg):
        if len(msg.ranges) < 2 or msg.angle_increment <= 0.0:
            return
        ranges_out, intensities_out = resample_arrays(
            msg.ranges, msg.intensities, msg.angle_min, msg.angle_increment, self._n
        )
        out = LaserScan()
        out.header = msg.header
        out.angle_min = 0.0
        out.angle_increment = TWO_PI / self._n
        out.angle_max = out.angle_increment * (self._n - 1)
        out.scan_time = msg.scan_time
        out.time_increment = msg.scan_time / self._n if msg.scan_time > 0.0 else 0.0
        out.range_min = msg.range_min
        out.range_max = msg.range_max
        out.ranges = ranges_out
        out.intensities = intensities_out if intensities_out is not None else []
        self._pub.publish(out)


def main():
    rclpy.init()
    node = ScanResampler()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
