import argparse
import math
import os

from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import Create3, event


parser = argparse.ArgumentParser()
parser.add_argument("x", type=float)
parser.add_argument("y", type=float)
parser.add_argument("yaw")
args = parser.parse_args()

robot = Create3(
    Bluetooth(
        name=os.getenv("CREATE3_BLUETOOTH_NAME"),
        address=os.getenv("CREATE3_BLUETOOTH_ADDRESS"),
    )
)


@event(robot.when_play)
async def play(robot: Create3) -> None:
    if args.yaw.lower() == "none":
        await robot.navigate_to(args.x, args.y)
    else:
        await robot.navigate_to(args.x, args.y, math.degrees(float(args.yaw)))
    await robot.stop()
    await robot.disconnect()
    await robot._backend.disconnect()
    robot._run = False
    robot._loop.stop()


robot.play()