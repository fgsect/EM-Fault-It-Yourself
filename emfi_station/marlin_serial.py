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
import serial
import logging


class MarlinSerial:
    """
    Manages serial connection to Marlin-based controller board.
    """
    def __init__(self, tty: str, sim: bool = False) -> None:
        """
        Connects to Marlin-based controller board.
        :param tty: Serial port to connect to.
        :param sim: Simulate serial connection if True.
        """
        self.log = logging.getLogger(__name__)
        self.sim = sim
        if not self.sim:
            self.ser = serial.Serial(port=tty, baudrate=115200, timeout=0.25)
            self.clear()

    def clear(self) -> None:
        """
        Clears serial input buffer.
        :return: None
        """
        if self.sim:
            self.log.info('Clearing serial buffer.')
        else:
            self.ser.flush()
            self.ser.reset_input_buffer()

    def read(self) -> bytes:
        """
        Reads a line from serial interface.
        :return: Message
        """
        if self.sim:
            time.sleep(0.5)
            return b'ok\n'
        else:
            msg = self.ser.readline()
            self.log.debug('Read from serial port: {:s}'.format(str(msg)))
            return msg

    def close(self) -> None:
        """
        Closes serial port.
        :return: None
        """
        self.log.info('Closing serial port.')
        if not self.sim:
            self.ser.close()

    def cmd(self, cmd: str) -> None:
        """
        Sends command via serial.
        :param cmd: Command string (e.g.: 'M122')
        :return: None
        """
        if self.sim:
            self.log.info('Sending: {:s}'.format(str(cmd)))
        else:
            self.log.debug('Write to serial port: {:s}'.format(str(cmd)))
            self.ser.write((cmd + '\n').encode())
            self.ser.flush()
