# Test for connecting to and controlling the Create 3 via Bluetooth
This is a guide for a test to try to control the **iRobot Create 3** with Bluetooth
The goal of this test is simple:

**You press Run in VS Code → the robot drives forward for 3 seconds → the robot stops.**

For this test you do not need ROS 2, WSL, or Wi-Fi.

---

## 1. What do you need?

For this test you need:

* A Windows PC
* Visual Studio Code
* An iRobot Create 3
* Bluetooth on the PC
* Internet connection during installation
* Python 3.11

The Create 3 is ultimately controlled directly from Python via Bluetooth.

The connection looks like this:

**VS Code → Python → Bluetooth → Create 3**

---

## 2. Installing Python 3.11

For this test we use Python 3.11.

Open **PowerShell** and type:

```powershell
py -3.11 --version
```

If Python 3.11 is installed, you will get for example:

```text
Python 3.11.9
```

If you get an error message that Python 3.11 cannot be found, Python 3.11 must first be installed.

> Note: if another Python version is already installed on the computer, you do not need to remove it. Different Python versions can coexist.

---

## 3. Creating a project folder

Create a new folder on the desktop for example:

```text
Create3
```

Then open this folder in **Visual Studio Code**.

---

## 4. Creating a virtual environment

Open in VS Code:

**Terminal → New Terminal**

Type:

```powershell
py -3.11 -m venv .venv
```

This creates a separate Python environment in the project folder.

You will now get for example:

```text
Create3
├── .venv
```

This `.venv` ensures that the programs and packages for this project stay separate from other Python projects.

---

## 5. Activating the virtual environment

Type in the same terminal:

```powershell
.venv\Scripts\Activate.ps1
```

If this succeeds, the terminal starts with:

```text
(.venv)
```

---

## 6. Installing the iRobot Python SDK

The Python SDK is the software that allows Python to communicate with the Create 3.

Install it with:

```powershell
pip install irobot-edu-sdk
```

Wait until the installation is completely done.

---

## 7. Creating a Python file

Create a new file in VS Code with the name:

```text
control.py
```

Put in it:

```python
from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import event, Root

robot = Root(Bluetooth())

@event(robot.when_play)
async def play(robot):
    await robot.set_wheel_speeds(20, 20)
    await robot.wait(3)
    await robot.set_wheel_speeds(0, 0)

robot.play()
```

### What does this code do?

This line creates a Bluetooth connection:

```python
robot = Root(Bluetooth())
```

Then the function is started when the program begins:

```python
@event(robot.when_play)
```

This line makes both wheels turn at speed 20:

```python
await robot.set_wheel_speeds(20, 20)
```

Because both wheels have the same speed, the robot drives forward.

Then Python waits 3 seconds:

```python
await robot.wait(3)
```

And finally both wheels are stopped:

```python
await robot.set_wheel_speeds(0, 0)
```

---

## 8. Preparing the Create 3

Turn on the Create 3.

Make sure that:

* the robot is turned on;
* Bluetooth is available;
* no one else is connected to the robot;
* there is sufficient free space in front of the robot.

Place the robot, for example, on the floor with a few meters of free space in front of it.

You do **not** need to be connected to the robot's Wi-Fi network for this test.

You also do not need to first add the robot manually via the regular Windows Bluetooth settings. The iRobot Python SDK finds the robot itself via Bluetooth.

---

## 9. Running the program

You can start the program directly from VS Code.

Open `control.py` and click in the top right on:

**▶ Run Python File**

You can also start it from the terminal:

```powershell
python control.py
```

In the terminal, for example, appears:

```text
Run event loop.
Connecting to iRobot-XXXXXXXX
```

If the connection succeeded, the code is executed.

The robot will then:

**Drive forward for 3 seconds → stop.**

---

## 10. If it works

If everything goes well, you now have a working connection:

```text
Visual Studio Code
        ↓
    Python 3.11
        ↓
 iRobot Python SDK
        ↓
     Bluetooth
        ↓
     Create 3
```

From here you can expand the code further, for example to:

* make the robot drive backwards;
* make it turn left and right;
* control the robot with keys;
* read out sensors;
* make it drive a specific route;
* make the robot part of a larger program.

---

## 11. Common problems

### The terminal does not show `(.venv)`

Reactivate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

### Python is using the wrong version

Check:

```powershell
python --version
```

For this test this should be approximately:

```text
Python 3.11.x
```

### The robot is not found

Check:

* is the Create 3 turned on?
* is someone else connected to it?
* is the robot close to the computer?
* is `python.irobot.com` closed?
* is Bluetooth enabled on the computer?

Then try to start the program again.

### The robot drives too fast

Lower, for example:

```python
await robot.set_wheel_speeds(20, 20)
```

to:

```python
await robot.set_wheel_speeds(10, 10)
```

### The robot drives too long

Lower:

```python
await robot.wait(3)
```

for example to:

```python
await robot.wait(1)
```

---

## Important

Always use an **open space** for the first test. The robot executes the driving command without taking obstacles into account.

This simple test only uses **Python + Bluetooth**. ROS 2, WSL, and Wi-Fi are not needed for this first test.
