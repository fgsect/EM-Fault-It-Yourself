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

import json


class State:
    """
    Holds the state of the EMFI station.
    It has three modes: manual mode, joystick mode and attack mode.
    """
    MANUAL_MODE = 'Manual'
    JOYSTICK_MODE = 'Joystick'
    ATTACK_MODE = 'Attack'

    def __init__(self, attacks) -> None:
        """
        Initialize state
        :param attacks: List of available attack names
        """
        self.mode = self.MANUAL_MODE
        self.position = [0, 0, 0]
        self.temperature = 0
        self.progress = 0
        self.attacks = attacks
        self.safe_z = 100

    def joystick_enabled(self) -> bool:
        """
        Checks whether joystick mode is enabled.
        :return: True if enabled
        """
        if self.mode == self.JOYSTICK_MODE:
            return True
        else:
            return False

    def attack_enabled(self) -> bool:
        """
        Checks whether attack mode is enabled.
        :return: True if enabled
        """
        if self.mode == self.ATTACK_MODE:
            return True
        else:
            return False

    def to_json(self) -> str:
        """
        Converts state variables to JSON.
        :return: State as JSON
        """
        return json.dumps({
            'type': 'state',
            'state': {
                'mode': self.mode,
                'position': '{:.6f} {:.6f} {:.6f}'.format(*self.position),
                'temperature': '{:.2f}'.format(self.temperature),
                'attacks': self.attacks,
                'progress': '{:.2f}'.format(self.progress * 100),
                'safe_z': self.safe_z
            }
        })
