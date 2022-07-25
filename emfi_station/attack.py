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

import logging


class Attack:
    """
    Base class for the attack implementations.
    """
    def __init__(self, start_pos: tuple[float, float, float], end_pos: tuple[float, float, float], step_size: int,
                 max_target_temp: float = 40, cooling: float = 0):
        """
        Initializes attack settings and attack hardware.
        :param start_pos: Start position of attack.
        :param end_pos: End positions of attack.
        :param step_size: End positions of attack.
        :param max_target_temp: Maximum target temperature before attack is paused.
        :param cooling: Target cooling fan speed (0-1)
        """
        self.log = logging.getLogger(__name__)
        self.start_pos = start_pos or [0, 0, 0]
        self.end_pos = end_pos or [0, 0, 0]
        self.step_size = step_size or 1
        self.max_target_temp = max_target_temp
        self.cooling = cooling

    @staticmethod
    def name() -> str:
        """
        Returns name of target/attack.
        :return: Attack name
        """
        return 'Default'

    def init(self) -> None:
        """
        Initialize hardware and define e.g. ChipShouter settings.
        :return: None
        """
        return None

    def shout(self) -> None:
        """
        Shout procedure.
        :return: None
        """
        return None

    def was_successful(self) -> bool:
        """
        Determines if attack was successful or not.
        Returns True if successful.
        :return: True or False
        """
        return False

    def reset_target(self) -> None:
        """
        Resets the target after an attack.
        :return: None
        """
        return None

    def critical_check(self) -> bool:
        """
        Runs critical checks after every shout. May wait some time.
        Returns False if check failed which leads to a shutdown.
        :return: True or False
        """
        return True
