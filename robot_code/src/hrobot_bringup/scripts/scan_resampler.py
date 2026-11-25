#!/usr/bin/env python3
"""Remuestrea sensor_msgs/LaserScan a un número FIJO de rayos.

El LD19 real entrega entre ~500 y 504 lecturas por vuelta (varía). slam_toolbox (Karto) fija el tamaño con
el primer scan y avisa "LaserRangeScan contains N range readings, expected M" con cualquier otro.
Este nodo lee `scan_raw` (driver) y publica `scan` con SIEMPRE `num_beams` rayos y los mismos ángulos.
Usa el vecino más cercano (no interpola, para no inventar distancias en los bordes de los obstáculos).
Solo robot real: el sensor simulado de Gazebo ya entrega un número fijo de rayos.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

TWO_PI = 2.0 * math.pi


def resample_arrays(ranges, intensities, angle_min, angle_increment, num_beams):
    """Devuelve (ranges, intensities) con `num_beams` rayos repartidos en 0..2*pi.

    El rayo de salida k apunta al ángulo k * (2*pi / num_beams). Para cada uno se toma la lectura de
    ENTRADA más cercana a ese ángulo. Si el scan de entrada no cubre una vuelta completa, los rayos fuera
    de su rango quedan en inf (sin lectura).
    `intensities` puede ser None o tener otro largo que `ranges`: en ese caso la salida va sin
    intensidades (se devuelve None en su lugar).
    Python puro: ~500 rayos a 10 Hz no justifican depender de numpy.
    """
    n_in = len(ranges)
    out_inc = TWO_PI / num_beams
    # La entrada cubre la vuelta si sus rayos suman 2*pi (con tolerancia de un rayo y medio).
    full_circle = n_in * angle_increment >= TWO_PI - 1.5 * angle_increment
    use_intensities = intensities is not None and len(intensities) == n_in

    ranges_out = []
    intensities_out = [] if use_intensities else None
    for k in range(num_beams):
        # Ángulo del rayo k respecto al inicio del scan de entrada, en [0, 2*pi).
        phi = (k * out_inc - angle_min) % TWO_PI
        i = int(round(phi / angle_increment))
        if i >= n_in:
            if full_circle:
                i -= n_in  # se cierra el círculo
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
        # 500 = resolución nominal del LD19 y lo que genera el sensor de Gazebo (real y simulación coinciden).
        self.declare_parameter("num_beams", 500)
        self._n = int(self.get_parameter("num_beams").value)
        if self._n < 2:
            raise ValueError("num_beams debe ser >= 2")

        # RELIABLE empareja con suscriptores RELIABLE (Nav2) y BEST_EFFORT (slam_toolbox, RViz).
        output_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE)
        self._pub = self.create_publisher(
            LaserScan, self.get_parameter("output_topic").value, output_qos
        )
        # Sensor-data (BEST_EFFORT) empareja con un driver RELIABLE o BEST_EFFORT.
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
