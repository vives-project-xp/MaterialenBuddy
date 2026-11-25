#!/usr/bin/env python3
"""Republica nav_msgs/Odometry de BEST_EFFORT a RELIABLE.

El Create 3 publica /<ns>/odom con QoS BEST_EFFORT y depth 1. Los nodos de Nav2 (controller_server,
bt_navigator) se suscriben con RELIABLE y nunca emparejan con ese publicador. Este nodo se suscribe con
el QoS del sensor y republica el MISMO mensaje en `odom_reliable` (nombre relativo: respeta el namespace).
Solo se usa con el robot real.
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

        # El callback solo reenvía el mensaje recibido.
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
