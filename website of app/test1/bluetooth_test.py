import os

from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import Create3, event


robot_name = os.getenv("CREATE3_BLUETOOTH_NAME")
robot = Create3(Bluetooth(robot_name))


@event(robot.when_play)
async def play(robot: Create3) -> None:
    print("Bluetooth verbonden. De robot rijdt 10 cm vooruit en daarna terug.")
    await robot.navigate_to(10, 0)
    await robot.navigate_to(0, 0)
    print("Proefrit voltooid.")


robot.play()