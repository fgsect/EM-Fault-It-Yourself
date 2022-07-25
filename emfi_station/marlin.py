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

import time
import logging
import threading
from typing import Optional

from .utils import get_device_fd
from .marlin_serial import MarlinSerial

BUSY_MSG = b'echo:busy: processing\n'
OK_MSG = b'ok\n'


class Marlin:
    """
    Controls XYZ stage setup.
    """
    def __init__(self, vendor_id: str, product_id: str, simulate: bool = False) -> None:
        """
        Connects to Marlin-based controller via serial port.
        Raises SerialException if serial port is unavailable.
        Raises IOError if board becomes unavailable.
        :param vendor_id: Vendor ID of board
        :param product_id: Product ID of board
        :param simulate: Simulate serial connection if True.
        """
        self.log = logging.getLogger(__name__)
        tty = None
        try:
            if not simulate:
                tty = get_device_fd(vendor_id, product_id, 'tty')
            else:
                self.log.critical('Simulation active.')
        except FileNotFoundError:
            self.log.critical('Marlin board unavailable. Simulation active.')
            simulate = True
        self.ser = MarlinSerial(tty, simulate)
        self.continuous_movement = None
        self.safe_height = 100

    def close(self) -> None:
        """
        Closes connection to controller.
        :return: None
        """
        self.ser.close()

    def __wait_cmd_completed(self, max_tries: int = 10) -> bytes:
        """
        Waits for a command to be completed.
        HOST_KEEPALIVE_FEATURE has to be enabled in Marlin configuration.
        Marlin is expected to send a 'busy' message once a second (DEFAULT_KEEPALIVE_INTERVAL 1).
        :param max_tries: Maximum number of tries to receive 'ok' message.
        :return: All received messages
        """
        msg = b''
        try:
            counter = 0
            while True:
                res = self.ser.read()
                if res:
                    msg += res
                if res == BUSY_MSG:
                    counter = 0
                if res == OK_MSG:
                    break
                time.sleep(0.25)
                counter += 1
                if counter > max_tries:
                    raise IOError('Timeout while waiting for a command to be completed: {:s}'.format(str(msg)))

        except KeyboardInterrupt:
            self.emergency()
            raise

        return msg + self.ser.read()

    def __wait_move_completed(self) -> None:
        """
        Waits for movement to be completed (M400).
        :return: None
        """
        self.ser.clear()
        self.ser.cmd('M400')
        self.__wait_cmd_completed()

    def emergency(self) -> None:
        """
        Stops movement immediately but allows further commands (M410).
        :return: None
        """
        self.ser.cmd('M410')
        self.log.critical('Emergency stop initiated.')
        self.__wait_cmd_completed()

    def kill(self) -> None:
        """
        Kills Marlin without allowing further commands (M112).
        Reboot necessary.
        :return: None
        """
        self.ser.cmd('M112')
        self.log.critical('Killing Marlin. Reboot necessary.')
        self.__wait_cmd_completed()

    def get_position(self) -> tuple[float, float, float]:
        """
        Retrieves current position.
        :return: Position coordinates (x, y, z)
        """
        self.ser.cmd('M114')
        pos_str = str(self.ser.read())
        self.__wait_cmd_completed()
        try:
            s = pos_str.split(':')
            x = float(s[1].split(' ', 1)[0])
            y = float(s[2].split(' ', 1)[0])
            z = float(s[3].split(' ', 1)[0])
            return x, y, z
        except IndexError:
            self.log.critical('Could not retrieve position.')
            return 0, 0, 0

    def set_acceleration(self, acceleration: int) -> None:
        """
        Set preferred starting acceleration.
        :param acceleration: Acceleration in mm/s/s
        :return: None
        """
        self.ser.cmd('M204 T' + str(acceleration))
        self.__wait_cmd_completed()

    def move(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None,
             feed_rate: float = 5) -> None:
        """
        Moves to given position. Set coordinate to None if axis should not move.
        :param x: X coordinate.
        :param y: Y coordinate.
        :param z: Z coordinate.
        :param feed_rate: Speed in mm/s.
        :return: None
        """
        if z is not None and not self.is_safe_height(z):
            self.log.critical('Moving to this position {:s} is not safe. Aborting.'.format(str((x, y, z))))
            return
        cmd = 'G0 F{:f}'.format(feed_rate * 60)
        if x is not None:
            cmd += 'X{:f}'.format(x)
        if y is not None:
            cmd += 'Y{:f}'.format(y)
        if z is not None:
            cmd += 'Z{:f}'.format(z)
        self.ser.cmd(cmd)
        self.log.info('Moving to X={:s}, Y={:s}, Z={:s}.'.format(str(x), str(y), str(z)))
        self.__wait_cmd_completed()
        self.__wait_move_completed()

    def relative_move(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None,
                      feed_rate: float = 5) -> None:
        """
        Moves relative to current position.
        :param x: Distance on X axis (+/-).
        :param y: Distance on Y axis (+/-).
        :param z: Distance on Z axis (+/-).
        :param feed_rate: Speed in mm/s.
        :return: None
        """
        pos = self.get_position()
        if not self.is_safe_height(pos[2] + z):
            self.log.critical('Moving to this position is not safe. Aborting.')
        self.relative_mode(True)
        self.move(x, y, z, feed_rate)
        self.relative_mode(False)

    def relative_mode(self, enable: bool) -> None:
        """
        Enables or disables relative position mode.
        :param enable: If true, enable relative position mode.
        :return: None
        """
        if enable:
            self.ser.cmd('G91')
            self.__wait_cmd_completed()
        else:
            self.ser.cmd('G90')
            self.__wait_cmd_completed()

    def continuous_move(self, x: float, y: float, z: float, feed_rate: int, step: int = 1) -> None:
        """
        Moves and waits until move is finished.
        Doesn't wait for confirmation but waits a defined amount of time.
        :param x: Distance on X axis (+/-).
        :param y: Distance on Y axis (+/-).
        :param z: Distance on Z axis (+/-).
        :param feed_rate: Feed rate to move with.
        :param step: Distance per step.
        :return: None
        """
        cmd = 'G0 F{:d} '.format(feed_rate * 60)
        if x:
            cmd += 'X{:f}'.format(step * x)
        if y:
            cmd += 'Y{:f}'.format(step * y)
        if z:
            cmd += 'Z{:f}'.format(step * z)
        self.ser.cmd(cmd)
        self.__wait_move_completed()

    def continuous_update(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None):
        """
        Starts or updates continuous movement.
        :param x: None = don't adjust movement, 0 = stop, -1 = move backward, 1 move forward.
        :param y: None = don't adjust movement, 0 = stop, -1 = move backward, 1 move forward.
        :param z: None = don't adjust movement, 0 = stop, -1 = move backward, 1 move forward.
        :return: None
        """
        if not self.continuous_movement:
            self.continuous_movement = ContinuousMove(self)
            self.continuous_movement.update(x, y, z)
            self.continuous_movement.start()
        else:
            if not self.continuous_movement.update(x, y, z):
                self.continuous_movement = None

    def save_pos(self, slot: int = 0) -> None:
        """
        Saves current position.
        :param slot: Slot number to save position.
        :return: None
        """
        self.ser.cmd('G60 S{:d}'.format(slot))
        self.__wait_cmd_completed()

    def return_to_pos(self, x: bool = True, y: bool = True, z: bool = True, slot: int = 0) -> None:
        """
        Moves to previously saved position.
        :param x: If true, move X axis.
        :param y: If true, move Y axis.
        :param z: If true, move Z axis.
        :param slot: Slot of saved position.
        :return: None
        """
        cmd = 'G61 '
        if x is not None:
            cmd += 'X'
        if y is not None:
            cmd += 'Y'
        if z is not None:
            cmd += 'Z'
        cmd += ' S{:d}'.format(slot)
        self.ser.cmd(cmd)
        self.__wait_cmd_completed()

    def home(self, x: bool = False, y: bool = False, z: bool = False) -> None:
        """
        Homes one or more axles (G28).
        :param x: Homes x axis if True.
        :param y: Homes y axis if True.
        :param z: Homes z axis if True.
        :return: None
        """
        if x == y == z and not x:
            return
        cmd = 'G28'
        if x:
            cmd += ' X'
        if y:
            cmd += ' Y'
        if z:
            cmd += ' Z'
        self.ser.clear()
        self.ser.cmd(cmd)
        self.log.info('Homing axles: {:s}'.format(cmd.split('G28 ')[1]))
        self.__wait_cmd_completed()

    def set_safe_height(self, z: float) -> None:
        """
        Sets a Z limit for safe operation.
        :param z: Z coordinate.
        :return: None
        """
        self.log.info('Set safe z height to: {}'.format(z))
        self.safe_height = z

    def is_safe_height(self, z: float) -> bool:
        """
        Checks if z position is in the safe range.
        :param z: Z coordinate.
        :return: True if height is safe.
        """
        if z > self.safe_height:
            return False
        else:
            return True

    def set_fan_speed(self, speed: int, slot: int = 2) -> None:
        """
        Set fan speed. Target cooling fan is connected to slot 2.
        :param speed: Speed between 0-255.
        :param slot: Index of fan slot.
        :return: None
        """
        self.ser.cmd('M106 P{:d} S{:d}'.format(slot, speed))
        self.__wait_cmd_completed()


class ContinuousMove:
    """
    Handles continuous movement.
    """
    def __init__(self, marlin: Marlin, feed_rate: int = 1) -> None:
        """
        Initializes but doesn't start continuous movement.
        :param marlin: Instance of Marlin class.
        :param feed_rate: Feed rate to move with.
        :return: None
        """
        self.marlin = marlin
        self.active = [0.0, 0.0, 0.0]
        self.feed_rate = feed_rate
        self.running = False
        self.thread = threading.Thread(target=self.__run)

    def __run(self) -> None:
        """
        Movement loop. Should be run as a thread.
        :return: None
        """
        self.marlin.relative_mode(True)
        while self.running:
            self.marlin.continuous_move(*self.active, self.feed_rate)
        self.marlin.relative_mode(False)

    def update(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None) -> bool:
        """
        Updates movement.
        :param x: None = don't adjust movement, 0 = stop, -1 = move backward, 1 move forward
        :param y: None = don't adjust movement, 0 = stop, -1 = move backward, 1 move forward
        :param z: None = don't adjust movement, 0 = stop, -1 = move backward, 1 move forward
        :return: True if still moving, False if no axis is moving
        """
        if x is not None:
            self.active[0] = x
        if y is not None:
            self.active[1] = y
        if z is not None:
            self.active[2] = z
        if set(self.active) == {0, 0, 0}:
            self.stop()
            return False
        else:
            return True

    def start(self) -> None:
        """
        Starts continuous movement.
        :return: None
        """
        self.running = True
        self.thread.start()

    def stop(self) -> None:
        """
        Stops continuous movement.
        :return: None
        """
        self.running = False
        self.thread.join()
