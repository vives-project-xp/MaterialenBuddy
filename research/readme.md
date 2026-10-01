# ROS 2 Jazzy setup on Ubuntu 24.04 (arm64)

Tested on an arm64 Ubuntu 24.04 machine. Paste each command **as a single line**, one block at a time. Line-wrapping when copying from PDFs or web pages breaks commands.

## 1. Add the missing `noble-updates` / `noble-backports` suites

Without this, `ros-jazzy-ros-base` fails with `liblz4-dev` / `libzstd-dev` version errors.

```bash
sudo tee /etc/apt/sources.list.d/ubuntu-updates.sources > /dev/null <<'EOF'
Types: deb
URIs: http://ports.ubuntu.com/ubuntu-ports
Suites: noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
```

> `ports.ubuntu.com` is the correct mirror for arm64. On x86_64, use `http://archive.ubuntu.com/ubuntu/` instead.

```bash
sudo apt update && sudo apt upgrade -y
```

The output should now include a `noble-updates` line.

## 2. Locale

```bash
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

## 3. Universe repository

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y universe
```

## 4. ROS 2 key and repository

```bash
sudo apt install -y curl
```

```bash
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

Note: it is `signed-by` (with a hyphen). Check the result with:

```bash
cat /etc/apt/sources.list.d/ros2.list
```

It must be one line.

## 5. Install ROS 2

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ros-jazzy-ros-base ros-dev-tools
```

## 6. rosdep

```bash
sudo rosdep init
rosdep update
```

If `rosdep init` says the file already exists, that is fine.

## 7. Auto-source ROS in every terminal

This only adds the line if it is not already in `~/.bashrc`:

```bash
grep -qxF "source /opt/ros/jazzy/setup.bash" ~/.bashrc || echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 8. Verify

```bash
ros2 topic list
```

To see the Create 3's topics, the robot must be on the same network as this machine (Wi-Fi, or Ethernet over USB-C), and its RMW setting must match yours. See the Setup and Networking pages in the Create 3 docs: https://iroboteducation.github.io/create3_docs/

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `liblz4-dev : Depends: liblz4-1 (= ...)` | Step 1 (add `noble-updates`) |
| `-o: command not found`, `syntax error near unexpected token` | Command was split across lines; paste as one line |
| `/opt/ros/jazzy/setup.bash: No such file` | ROS is not installed yet; finish step 5 |
| `/dev/null: Permission denied` | `> /dev/null` ended up on its own line; use `sudo tee` on one line |
| Wrong distro | Jazzy = Ubuntu 24.04, Humble = Ubuntu 22.04. Check `lsb_release -a` |

Remove a broken line from `.bashrc`:

```bash
sed -i '/opt\/ros\/jazzy\/setup.bash/d' ~/.bashrc
```

---

# Windows: ZQSD drive script (Create 3 over Bluetooth)

`py` defaults to Python 3.14 here, but the packages are in 3.11. Always use the 3.11 interpreter explicitly.

```powershell
py -3.11 -m pip install irobot-edu-sdk keyboard
$env:CREATE3_BLUETOOTH_NAME="YourRobotName"
py -3.11 drive.py
```

- Close any browser tab connected to the robot first (BLE allows one connection).
- Run from an open PowerShell window so errors stay visible.
- Max speed is about 30 cm/s, so keep `SPEED + TURN` under about 30 or clamp the wheel speeds.
