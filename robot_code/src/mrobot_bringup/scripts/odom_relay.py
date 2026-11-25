#!/usr/bin/env python3
"""Republish nav_msgs/Odometry from BEST_EFFORT to RELIABLE.

The Create 3 publishes /<ns>/odom with BEST_EFFORT QoS and depth 1. The Nav2 nodes (controller_server,
bt_navigator) subscribe with RELIABLE and never match that publisher. This node subscribes with the
sensor QoS and republishes the SAME message on `odom_reliable` (relative name: it respects the namespace).
Only used with the real robot.
"""

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data


class OdomRelay(Node):
    def __init__(self):
        super().__init__("odom_relay")

        self.declare_parameter("input_topic", "odom")
        self.declare_parameter("output_topic", "odom_reliable")

        output_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._pub = self.create_publisher(
            Odometry, self.get_parameter("output_topic").value, output_qos
        )

        # The callback only forwards the received message.
        self.create_subscription(
            Odometry,
            self.get_parameter("input_topic").value,
            self._pub.publish,
            qos_profile_sensor_data,
        )


def main():
    rclpy.init()
    node = OdomRelay()
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
