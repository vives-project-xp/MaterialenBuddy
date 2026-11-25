#!/usr/bin/env python3
"""Convert geometry_msgs/Twist into geometry_msgs/TwistStamped.

In ROS 2 Jazzy the diff_drive_controller receives TwistStamped on `diffdrive_controller/cmd_vel`, but the teleop
(teleop_twist_keyboard) and Nav2 publish Twist on `cmd_vel`. This node bridges the two.
Only used in simulation: the real Create 3 receives Twist directly on /r2/cmd_vel.
"""

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node


class CmdVelStamper(Node):
    def __init__(self):
        super().__init__("cmd_vel_stamper")

        self.declare_parameter("input_topic", "cmd_vel")
        self.declare_parameter("output_topic", "diffdrive_controller/cmd_vel")
        self._pub = self.create_publisher(
            TwistStamped, self.get_parameter("output_topic").value, qos_profile=10)
        self.create_subscription(Twist, self.get_parameter(
            "input_topic").value, self._on_twist, qos_profile=10)

    def _on_twist(self, msg):
        # With use_sim_time:=true the node clock is the Gazebo one.
        stamped_msg = TwistStamped()
        stamped_msg.header.stamp = self.get_clock().now().to_msg()
        stamped_msg.header.frame_id = "base_link"
        stamped_msg.twist = msg
        self._pub.publish(stamped_msg)


def main():
    rclpy.init()
    node = CmdVelStamper()
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
