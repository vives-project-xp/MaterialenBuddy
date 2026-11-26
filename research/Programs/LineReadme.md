\# Blue line follower (iRobot Create 3 + Raspberry Pi 5 + Logitech C270)



A single-file ROS 2 node that makes the Create 3 drive along a strip of blue tape on the floor, using only the webcam. It stops by itself at the end of the line.



\- Script: `line.py` (`line\_follower.py` in the source)

\- Robot: iRobot Create 3, topics under the `/r1` namespace

\- Computer: Raspberry Pi 5, Ubuntu 24.04, ROS 2 Jazzy

\- Camera: Logitech C270 HD webcam, published by `usb\_cam` on `/image\_raw`



\## How it works



1\. Each camera frame is shrunk to 320x240 and converted to HSV colour space.

2\. Pixels inside the blue HSV range are kept, then cleaned with a small open/close filter.

3\. The top part of the image is ignored (`--roi-top`), so blue objects on walls and shelves don't count.

4\. The remaining area is split into a \*\*near\*\* band (close to the robot) and a \*\*far\*\* band (further ahead). The centre of the largest blue blob in each band gives a horizontal error.

5\. The steering error is 65% near + 35% far. Angular speed is proportional to the error. Forward speed drops in sharp curves.

6\. If the line disappears, the robot turns slowly towards the side where it last saw it. After `--lost-timeout` seconds without a line it stops. This is also how it stops at the end of the tape.



It publishes `geometry\_msgs/Twist` to `/r1/cmd\_vel`.



\## Requirements



```

sudo apt install ros-jazzy-usb-cam ros-jazzy-cv-bridge python3-opencv python3-numpy

```



\- `robot1` must be in the `video` group (`sudo usermod -aG video robot1`, then log in again), otherwise the camera cannot be opened.

\- The `irobot\_create\_msgs` package is optional but recommended. Without it the script prints a warning and the bump/cliff stop is disabled (the Create 3 still stops itself on cliffs and bumps).

\- Do not run these commands with `sudo`; it does not have your ROS environment.



\## Setup



\*\*Tape.\*\* Use matte blue tape (painter's or masking tape). Shiny tape reflects the lights and loses its colour. A straight start is best for the first test.



\*\*Camera position.\*\* Mount the camera at the front, tilted slightly down, so it sees the floor about 0.5 to 1 m ahead. The tape should appear in the lower half of the picture.



\*\*Lighting.\*\* Auto-exposure changes the apparent colour. For consistent results, lock the exposure with `v4l2-ctl` and use similar lighting each time.



\## Usage



Start the camera in one terminal and leave it running: run python3 line.py --hsv-low 95,50,50 --speed 0.20



```

ros2 run usb\_cam usb\_cam\_node\_exe --ros-args \\

&#x20; -p video\_device:=/dev/video0 -p image\_width:=640 -p image\_height:=480 \\

&#x20; -p framerate:=15.0 -p pixel\_format:=yuyv

```



Check that frames arrive (about 15 Hz): `ros2 topic hz /image\_raw`



In a second terminal:



\*\*1. Check the colour range (optional).\*\*



```

python3 line.py --probe

```



Saves `probe.jpg` and prints the HSV values inside a small yellow box in the bottom centre of the picture. The tape must fill that box, otherwise it measures the floor instead (floor is hue \~20, blue tape is hue \~95-130). If the numbers look wrong, ignore them and use the defaults.



\*\*2. Dry run (the robot does not drive).\*\*



```

python3 line.py --dry-run --save-debug \~/line\_debug

```



Push the robot along the line by hand, then press Ctrl+C. Copy a few frames from `\~/line\_debug` to your PC (`scp`). In the saved frames, detected tape is green, the yellow lines mark the area being used, and the red dots show where the line is judged to be. Only the tape should be green below the upper yellow line.



\*\*3. Drive.\*\*



```

python3 line.py --speed 0.08

```



Place the robot facing along the line with the tape in the lower part of the picture. Keep a hand near the robot for the first runs. Stop with Ctrl+C.



\## Options



| Option | Default | Meaning |

|---|---|---|

| `--probe` | off | Measure the tape colour and exit |

| `--dry-run` | off | Do everything except send drive commands |

| `--hsv-low` | `95,90,50` | Lower HSV bound (OpenCV scale: H 0-179, S and V 0-255) |

| `--hsv-high` | `130,255,255` | Upper HSV bound |

| `--speed` | `0.10` | Maximum forward speed in m/s (limited to 0.02-0.2) |

| `--roi-top` | `0.45` | Ignore the image above this fraction of its height |

| `--lost-timeout` | `2.5` | Seconds without a line before stopping |

| `--max-time` | `120` | Stop after this many seconds |

| `--save-debug` | off | Folder for annotated debug frames (up to 300 are saved) |



Constants at the top of the script: `K\_ANG` (steering gain, 1.2), `MAX\_ANG` (0.6 rad/s), `MIN\_AREA` (smallest blob counted as line, 80 px), `SEARCH\_ANG` (turn speed when searching, 0.3 rad/s).



\## Tuning



| Problem | What to try |

|---|---|

| Tape is not detected (not green in debug frames) | Lower the saturation limit, e.g. `--hsv-low 95,50,50`; check the colour with `--probe` |

| Far part of the line is missed | Lower the saturation limit as above, or lower `MIN\_AREA` (e.g. 40) |

| Other blue things are detected | Raise `--roi-top` (e.g. 0.55) or raise the saturation limit, e.g. `--hsv-low 95,130,60` |

| Robot wobbles from side to side | Lower `K\_ANG` or `--speed` |

| Robot reacts too slowly in curves | Raise `K\_ANG` a little, or lower `--speed` |

| Loses the line in sharp corners | Lower `--speed` (e.g. 0.06), round the tape corners, or tilt the camera to see further ahead |

| Robot turns away from the line | Flip the sign in `ang = clamp(-K\_ANG \* err, ...)` |



\## Safety



\- The robot stops on a bump, cliff, stall or wheel-drop event (if `irobot\_create\_msgs` is installed), after `--max-time`, when camera frames stop arriving for more than 0.6 s, when the line is lost for `--lost-timeout`, and on Ctrl+C.

\- The top speed is limited to 0.2 m/s and defaults to 0.10 m/s.

\- Keep the robot away from stairs and edges, and keep a hand near it for the first runs.



\## Troubleshooting



\- \*\*Nothing happens and no output:\*\* the camera node is probably not running. The script warns after 4 seconds without frames. Check `ros2 topic hz /image\_raw`.

\- \*\*"Cannot open device" from `usb\_cam`:\*\* the user is not in the `video` group, or the session was not restarted after adding it. The C270 is `/dev/video0`; the other `/dev/video\*` devices on the Pi 5 are internal and can be ignored.

\- \*\*`ros2 topic list` shows no `/r1/...` topics:\*\* the Pi is not connected to the Create 3. Check the network link and that the same ROS domain/RMW settings are used on both.

\- \*\*Robot does not move but the log shows steering values:\*\* you may still be using `--dry-run`.



\## Limitations



\- Heading is controlled from what the camera sees on the floor. There is no obstacle avoidance beyond the Create 3's own bump and cliff sensors.

\- Works best on a floor that is clearly not blue, in steady lighting.

\- Sharp turns, gaps in the tape and crossing lines are not handled specially.

