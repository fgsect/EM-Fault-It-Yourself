# EM-Fault It Yourself
This repository contains supplementary hardware design files and software to our paper 
[*EM-Fault It Yourself: Building a Replicable EMFI Setup for Desktop and Server Hardware*](). 
You can view it as a starting point to build your own customizable and open-source electromagnetic fault injection 
setup.

- `emfi_station/` contains the main controller software
- `marlin/` contains [Marlin](https://marlinfw.org/) configuration files
- `hardware/` contains hardware design files for 3D-printable parts

Detailed information can be found in the `README.md` files of the subdirectories.

## Software
The main controller software is a Python package called `emfi_station`. It provides a web interface to control the XYZ
stage, watch camera and sensor data and orchestrate complete electromagnetic fault injection attacks. To install the 
package clone this repository and run `pip`:

```shell
git clone 
pip install .
```

You can run *EMFI Station* using the command line:

```shell
usage: emfi-station [-h] [-i HOST] [-p PORT] [-s] [-a ATTACK_DIR] [-l LOG_DIR] [--marlin MARLIN] [--cal_cam CAL_CAM] [--pos_cam POS_CAM] [-v]

EMFI Station - Orchestrate electromagnetic fault injection attacks

options:
  -h, --help            show this help message and exit
  -i HOST, --host HOST  hostname or ip address
  -p PORT, --port PORT  http port (websocket port = http port + 1)
  -s, --simulate        simulate connection to Marlin
  -a ATTACK_DIR, --attack_dir ATTACK_DIR
                        attack scripts directory
  -l LOG_DIR, --log_dir LOG_DIR
                        log files directory
  --marlin MARLIN       (vendor_id, product_id) of Marlin board
  --cal_cam CAL_CAM     (vendor_id, product_id) of calibration camera
  --pos_cam POS_CAM     (vendor_id, product_id) of positioning camera
  -v, --verbosity       enable info log level
```

### Attack Scripts
The *EMFI Station* has an interface in the form of an `Attack` base class (`attack.py`) to allow easy integration of 
task/attack scripts. Your own task/attack class should inherit from the base class and implement the required 
methods. Each class should have its own file and a unique name (name() method). You can specify a folder containing 
attack scripts in the command line parameters.

## Troubleshooting
If you experience a `select timeout` while running *EMFI Station* under Raspbian, please try to adjust the quirks 
parameter of the `uvcvideo` kernel module:

```shell
rmmod uvcvideo
modprobe uvcvideo quirks=0x80
```
