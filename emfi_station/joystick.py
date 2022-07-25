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

import evdev
import logging
import select
import threading

from .utils import get_device_fd

VENDOR_ID = '046d'      # Logitech Attack 3 Joystick
PRODUCT_ID = 'c214'     # Logitech Attack 3 Joystick

BUTTON_FIRE = 288   # attack
BUTTON_2 = 289      # step backwards
BUTTON_3 = 290      # step forwards
BUTTON_4 = 291      # step left
BUTTON_5 = 292      # step right
BUTTON_6 = 293      # home
BUTTON_7 = 294
BUTTON_8 = 295      # step down
BUTTON_9 = 296      # step up
BUTTON_10 = 297     # save position
BUTTON_11 = 298     # return to saved position

AXLES = ['X', 'Y', 'Z']


class Joystick:
    def __init__(self, marlin, feed_rate, step_dist=0.5):
        """
        Initializes a connected joystick. Currently only supports Logitech Attack 3 Joystick.
        Raises FileNotFoundError if the joystick is unavailable.
        :param marlin: Instance of Marlin to interact with the XYZ stage.
        :param step_dist: Step distance (per button press).
        """
        self.log = logging.getLogger(__name__)
        self.marlin = marlin
        self.step_dist = step_dist
        self.feed_rate = feed_rate
        self.dev = evdev.InputDevice(get_device_fd(VENDOR_ID, PRODUCT_ID, 'input'))
        # self.dev.grab()
        self.last_event = [0, 0, 0]
        self.stepping = True
        self.thread = None
        self.running = False

    def __loop(self):
        """
        Waits for events from joystick and handles them until self.running == False.
        :return: None
        """
        while self.running:
            select.select([self.dev], [], [], 0.2)
            event = self.dev.read_one()
            if event:
                self.__eval_axles()
                if event.value == 1:
                    self.__eval_buttons(event.code)

    def start(self):
        """
        Starts loop thread.
        :return: None
        """
        self.running = True
        self.thread = threading.Thread(target=self.__loop)
        self.thread.start()

    def stop(self):
        """
        Stops thread.
        :return: None
        """
        self.running = False
        self.thread.join()

    def close(self):
        """
        Closes device.
        :return: None
        """
        # self.dev.ungrab()
        self.dev.close()

    def __eval_axles(self):
        """
        Evaluates axis data and calls movement methods.
        :return: None
        """
        value = [
            self.dev.absinfo(evdev.ecodes.ABS_X).value,
            self.dev.absinfo(evdev.ecodes.ABS_Y).value,
            self.dev.absinfo(evdev.ecodes.ABS_Z).value
        ]
        # debounce axles
        for axis in [0, 1, 2]:
            if value[axis] > 215 and self.last_event[axis] == 0:
                self.__move(axis, 1)
                self.last_event[axis] = 1
            if value[axis] < 175 and self.last_event[axis] == 1:
                self.__halt(axis)
                self.last_event[axis] = 0
            if value[axis] < 40 and self.last_event[axis] == 0:
                self.__move(axis, -1)
                self.last_event[axis] = -1
            if value[axis] > 80 and self.last_event[axis] == -1:
                self.__halt(axis)
                self.last_event[axis] = 0

    def __eval_buttons(self, code):
        """
        Evaluates buttons and calls movement methods.
        :return: None
        """
        if code == BUTTON_FIRE:
            self.__get_position()
        elif code == BUTTON_2:
            self.__step(1, 1)
        elif code == BUTTON_3:
            self.__step(1, -1)
        elif code == BUTTON_4:
            self.__step(0, -1)
        elif code == BUTTON_5:
            self.__step(0, 1)
        elif code == BUTTON_6:
            self.__home()
        elif code == BUTTON_7:
            self.__emergency()
        elif code == BUTTON_8:
            self.__step(2, -1)
        elif code == BUTTON_9:
            self.__step(2, 1)
        elif code == BUTTON_10:
            self.__save_pos()
        elif code == BUTTON_11:
            self.__return_pos()
        else:
            self.log.warning('Unknown button pressed.')

    def __move(self, axis, direction):
        """
        Starts continuous movement.
        :param axis: 0 = X, 1 = Y, 2 = Z
        :param direction: -1 = backwards, 1 = forwards
        :return: None
        """
        self.stepping = False
        self.log.debug('Starting movement on axis {:s}.'.format(AXLES[axis]))
        d = [None, None, None]
        d[axis] = direction
        self.marlin.continuous_update(*d)

    def __halt(self, axis):
        """
        Stops continuous movement.
        :param axis: 0 = X, 1 = Y, 2 = Z
        :return: None
        """
        self.stepping = True
        self.log.debug('Stopping movement on axis {:s}.'.format(AXLES[axis]))
        d = [None, None, None]
        d[axis] = 0
        self.marlin.continuous_update(*d)

    def __step(self, axis, direction):
        """
        Moves one step on given axis.
        :param axis: 0 = X, 1 = Y, 2 = Z
        :param direction: -1 = backwards, 1 = forwards
        :return: None
        """
        if self.stepping:
            step = [None, None, None]
            step[axis] = direction * self.step_dist
            self.log.debug('Stepping on axis {} to {}.'.format(AXLES[axis], step[axis]))
            self.marlin.relative_move(*step, self.feed_rate)

    def __get_position(self):
        """
        Prints current position.
        :return: None
        """
        self.log.info(str(self.marlin.get_position()))

    def __home(self):
        """
        Homes all axles.
        :return: None
        """
        if self.stepping:
            self.log.debug('Homing all axles.')
            self.marlin.home(True, True, True)

    def __save_pos(self):
        """
        Saves current position.
        :return: None
        """
        if self.stepping:
            self.log.debug('Saving current position.')
            self.marlin.save_pos()

    def __return_pos(self):
        """
        Returns to saved position.
        :return: None
        """
        if self.stepping:
            self.log.debug('Returning to saved position.')
            self.marlin.return_to_pos()

    def __emergency(self):
        """
        Stops all movements immediately.
        :return: None
        """
        self.marlin.emergency()
