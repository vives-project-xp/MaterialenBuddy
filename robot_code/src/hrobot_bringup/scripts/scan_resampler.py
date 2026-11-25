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

    Idea: el rayo de salida k apunta al ángulo k * (2*pi / num_beams). Para cada uno se busca el rayo de
    ENTRADA más cercano a ese ángulo.

    Pistas:
      * Ángulo del rayo k respecto al inicio del scan de entrada:
            phi = (k * out_inc - angle_min) % TWO_PI
      * Índice de entrada más cercano: i = int(round(phi / angle_increment))
      * Si i >= n_in y la entrada cubre la vuelta completa, i -= n_in (se cierra el círculo).
        Si no la cubre, ese rayo no tiene lectura: usa math.inf.
      * `intensities` puede ser None o tener otro largo que `ranges`: en ese caso la salida va sin
        intensidades (devuelve None en su lugar).
    Python puro: ~500 rayos a 10 Hz no justifican depender de numpy.
    """
    # TODO 5: implementa el remuestreo siguiendo las pistas de arriba.
    raise NotImplementedError


class ScanResampler(Node):
    def __init__(self):
        super().__init__("scan_resampler")

        # TODO 1: declara los parámetros input_topic ("scan_raw"), output_topic ("scan") y num_beams.
        #         Decisión pendiente: ¿504 (como el proyecto anterior) o 500 (como el LD19 nominal y
        #         el sensor de Gazebo)? Recomendado: 500, así real y simulación coinciden.
        #         Valida que num_beams >= 2 (si no, lanza ValueError).

        # TODO 2: QoS de salida RELIABLE (depth=5). RELIABLE empareja con suscriptores RELIABLE (Nav2)
        #         y con BEST_EFFORT (slam_toolbox, RViz). Crea el publisher de LaserScan en output_topic.

        # TODO 3: suscripción a input_topic con qos_profile_sensor_data y callback self._on_scan.

    def _on_scan(self, msg):
        # TODO 4: si msg.ranges tiene menos de 2 elementos o msg.angle_increment <= 0, no hagas nada.
        #         Si no: llama a resample_arrays(...) y construye un LaserScan nuevo copiando
        #         header, scan_time, range_min y range_max, y poniendo:
        #           angle_min = 0.0
        #           angle_increment = TWO_PI / num_beams
        #           angle_max = angle_increment * (num_beams - 1)
        #           time_increment = scan_time / num_beams (o 0.0 si scan_time <= 0)
        #           ranges / intensities = resultado del remuestreo ([] si no hay intensidades)
        #         y publícalo.
        pass


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
