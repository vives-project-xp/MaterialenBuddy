# First local test

## Installation

Open PowerShell in this folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Starting

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Then open http://127.0.0.1:8000 in the browser. The default mode is `mock`: after a click, the status `arrived` is shown after two seconds.

## What was built?

This test app consists of a FastAPI server, a simple web page, and `waypoints.json` with the locations. The web page fetches the locations and sends a navigation order to the server when a click occurs. The server returns the status `en route`, `arrived`, `cancelled`, or `error`.

There are two modes: `mock` to test the software safely without a robot, and `bluetooth` to actually drive the Create 3 using the official `irobot-edu-sdk`. A new order cancels a previous order, and stuck navigation gets a timeout.

With `reset_origin.py`, the current position of the robot can be set once as the new origin `(0, 0)`. The waypoints are stored as absolute coordinates in centimeters.

The robot configuration is set to `10.10.234.52` by default. Check the network connection first:

```powershell
Test-Connection 10.10.234.52 -Count 1
Test-NetConnection 10.10.234.52 -Port 80
```

The default mode is `mock`. For real Bluetooth navigation, start the server with:

```powershell
$env:CREATE3_MODE = "bluetooth"
python -m uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

After that, the buttons on http://127.0.0.1:8001 actually drive the Create 3 to the chosen waypoint. The server uses a timeout of 60 seconds per order.

## First physical Bluetooth test

Place the Create 3 freely on the floor and make sure there is at least 1 meter of space around the robot. Turn on Bluetooth on the laptop and then run:

```powershell
python bluetooth_test.py
```

## Setting a new origin

Place the robot on the desired current starting position and run this once. The robot does not drive; its current position becomes `(0, 0)`.

```powershell
python reset_origin.py
```

The robot drives 10 cm forward and then back to the starting point. You can optionally provide the Bluetooth name:

```powershell
$env:CREATE3_BLUETOOTH_NAME = "Create 3"
python bluetooth_test.py
```