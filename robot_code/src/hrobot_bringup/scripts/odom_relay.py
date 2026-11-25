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

        # TODO 1: declara los parámetros input_topic (por defecto "odom") y
        #         output_topic (por defecto "odom_reliable") con self.declare_parameter(...).

        # TODO 2: crea el QoS de salida: QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE).

        # TODO 3: crea el publisher de Odometry en el topic output_topic con ese QoS.
        #         Guárdalo en self._pub. Lee el valor del parámetro con self.get_parameter(...).value.

        # TODO 4: crea la suscripción a input_topic con qos_profile_sensor_data (BEST_EFFORT).
        #         El callback solo reenvía el mensaje recibido: puede ser self._pub.publish directamente.


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
