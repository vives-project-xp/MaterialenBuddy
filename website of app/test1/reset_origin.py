import asyncio
import os

from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import Create3


async def reset_origin() -> None:
    robot = Create3(
        Bluetooth(
            name=os.getenv("CREATE3_BLUETOOTH_NAME"),
            address=os.getenv("CREATE3_BLUETOOTH_ADDRESS"),
        )
    )
    await robot._backend.connect()
    await robot.reset_navigation()
    await robot.stop()
    await robot.disconnect()
    await robot._backend.disconnect()
    print("Nieuw nulpunt ingesteld op de huidige robotpositie.")


asyncio.run(reset_origin())