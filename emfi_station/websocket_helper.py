# EMFI Station - Orchestrate electromagnetic fault injection attacks
# Copyright (C) 2022 Niclas Kühnapfel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import base64
import threading
import logging

from .config import Config
from .marlin import Marlin
from .microscope import Microscope
from .joystick import Joystick
from .thermal_camera import ThermalCamera
from .websocket_state import State
from .attack_worker import AttackWorker
from .attack_importer import AttackImporter


class WebSocketHelper:
    """
    Manages server state and tasks. Connects websocket server and hardware.
    """
    def __init__(self, config: Config) -> None:
        """
        Initialize variables and devices.2
        :param config: Configuration object.
        """
        self.log = logging.getLogger(__name__)
        self.importer = AttackImporter(config.attack_dir)
        self.marlin = Marlin(*config.marlin, config.simulate)
        self.microscope = Microscope(*config.positioning_cam, None)
        self.calibration = Microscope(*config.calibration_cam, None)
        self.thermal_camera = ThermalCamera()
        self.thermal_camera.start()
        self.attack_runner = AttackWorker(self.importer, self.marlin, self.thermal_camera, config.log_dir)
        self.joystick = None
        self.task = threading.Thread()
        self.state = State(self.importer.get_attack_names())

    def step(self, speed: float, x: float, y: float, z: float) -> bool:
        """
        Invokes a relative move of the XYZ stage.
        :param speed: Maximum speed.
        :param x: X coordinate to move to.
        :param y: Y coordinate to move to.
        :param z: Z coordinate to move to.
        :return: True if possible, False if currently not possible.
        """
        if not (self.state.attack_enabled() and self.state.joystick_enabled()):
            self.task = threading.Thread(target=self.marlin.relative_move, args=(x, y, z, speed,))
            self.task.start()
            return True
        else:
            return False

    def home(self, x: bool, y: bool, z: bool) -> bool:
        """
        Invokes homing of specified axis.
        :param x: Homes X axis if True.
        :param y: Homes X axis if True.
        :param z: Homes X axis if True.
        :return: True if possible, False if not possible.
        """
        if not (self.state.attack_enabled() and self.state.joystick_enabled()):
            self.task = threading.Thread(target=self.marlin.home, args=(x, y, z,))
            self.task.start()
            return True
        else:
            return False

    def move(self, speed: float, x: float, y: float, z: float) -> bool:
        """
        Invokes an absolute move of the XYZ stage.
        :param speed: Maximum speed.
        :param x: X coordinate to move to.
        :param y: Y coordinate to move to.
        :param z: Z coordinate to move to.
        :return: True if possible, False if currently not possible.
        """
        if not (self.state.attack_enabled() and self.state.joystick_enabled()):
            self.task = threading.Thread(target=self.marlin.move, args=(x, y, z, speed,))
            self.task.start()
            return True
        else:
            return False

    def is_running(self) -> bool:
        """
        Checks whether a task is currently running or not.
        :return: True if a task is running, False if no task is running.
        """
        return self.task.is_alive()

    def on_first_connected(self) -> None:
        """
        Called when the first client is connected.
        Starts the microscope capture thread.
        :return: None
        """
        self.microscope.start()
        self.calibration.start()

    def on_last_disconnected(self) -> None:
        """
        Called when the last client is disconnected.
        Stops the microscope capture thread.
        :return: None
        """
        self.microscope.stop()
        self.calibration.stop()

    def get_microscope_frame(self) -> str:
        """
        Retrieves an image from the microscope camera.
        :return: Base64 encoded image.
        """
        return base64.b64encode(self.microscope.get_frame()).decode()

    def get_thermal_frame(self) -> str:
        """
        Retrieves an image from the thermal camera.
        :return: Base64 encoded image.
        """
        return base64.b64encode(self.thermal_camera.get_last_frame()).decode()

    def get_calibration_frame(self) -> str:
        """
        Retrieves an image from the microscope camera.
        :return: Base64 encoded image.
        """
        return base64.b64encode(self.calibration.get_frame()).decode()

    def shutdown(self) -> None:
        """
        Stops all task to allow a graceful shutdown.
        :return: None
        """
        if self.task.is_alive():
            if self.state.mode == self.state.JOYSTICK_MODE:
                self.disable_joystick()
            elif self.state.mode == self.state.ATTACK_MODE:
                self.stop_attack()
            else:
                self.task.join()

    def enable_joystick(self, speed: float, step: float) -> bool:
        """
        Enables joystick mode.
        :param speed: Maximum speed.
        :param step: Step size.
        :return: True if possible, False if not possible.
        """
        if self.state.attack_enabled() or self.state.joystick_enabled():
            return False

        if self.joystick is None:
            try:
                self.joystick = Joystick(self.marlin, speed, step)
            except FileNotFoundError:
                self.log.critical('Joystick is unavailable.')
                return False
        self.joystick.running = True
        self.task = threading.Thread(target=self.joystick.loop)
        self.task.start()
        self.state.mode = self.state.JOYSTICK_MODE
        return True

    def disable_joystick(self) -> bool:
        """
        Disables joystick mode.
        :return: True if successful.
        """
        if self.joystick is not None:
            self.joystick.running = False
            self.task.join()
        self.state.mode = self.state.MANUAL_MODE
        return True

    def get_state_json(self) -> str:
        """
        Returns current state as JSON.
        :return: State as JSON
        """
        self.update()
        return self.state.to_json()

    def update(self) -> None:
        """
        Updates the current server state.
        :return: None
        """
        self.state.temperature = self.thermal_camera.get_last_temperature()
        if self.state.attack_enabled():
            self.state.progress = self.attack_runner.get_progress()
            self.state.position = self.attack_runner.get_position()
            if not self.is_running():
                self.state.mode = self.state.MANUAL_MODE
        elif not self.is_running():
            self.state.position = self.marlin.get_position()

    def start_attack(self, name: str):
        """
        Starts an attack task.
        :param name: Name of the attack.
        :return: True if possible, False if not possible.
        """
        if self.state.attack_enabled() or self.state.joystick_enabled():
            return False
        if not self.attack_runner.load_attack(name):
            return False
        self.task = threading.Thread(target=self.attack_runner.run)
        self.task.start()
        self.state.mode = self.state.ATTACK_MODE
        return True

    def stop_attack(self) -> bool:
        """
        Stops a running attack.
        :return: True if was stopped, False if no attack is running.
        """
        if self.state.attack_enabled():
            self.attack_runner.stop()
            self.task.join()
            self.state.mode = self.state.MANUAL_MODE
            return True
        else:
            return False

    def set_safe_z(self, z):
        """
        Sets a maximum Z depth.
        :param z: Z depth in mm.
        :return: True if successful.
        """
        self.marlin.set_safe_height(float(z))
        self.state.safe_z = z
        return True
