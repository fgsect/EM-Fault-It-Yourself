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
from typing import Optional

from .marlin import Marlin
from .utils import compute_positions
from .attack_logger import AttackLogger
from .thermal_camera import ThermalCamera
from .attack_importer import AttackImporter


class AttackWorker:
    """
    Initializes and runs attacks.
    """
    def __init__(self, importer: AttackImporter, marlin: Marlin, thermal_cam: ThermalCamera,
                 log_dir: Optional[str]) -> None:
        """
        Initializes variables and attack logging.
        :param marlin: Marlin object.
        :param thermal_cam: ThermalCamera object.
        :param log_dir: Directory to store all log files.
        """
        self.log = logging.getLogger(__name__)
        self.attack = None
        self.marlin = marlin
        self.thermal_cam = thermal_cam
        self.running = False
        self.progress = 0
        self.position = [0, 0, 0]
        self.a_log = AttackLogger(log_dir)
        self.importer = importer

    def load_attack(self, name: str) -> bool:
        """
        Load attack class dynamically.
        :param name: Attack name.
        :return: True if successful.
        """
        cls = self.importer.get_attack_by_name(name)
        self.a_log.set_name(name)
        try:
            self.attack = cls()
        except TypeError:
            return False
        return True

    def get_progress(self) -> float:
        """
        Returns progress of currently running attack.
        :return: Progress percentage.
        """
        return self.progress

    def get_position(self) -> list[float, float, float]:
        """
        Returns current position.
        :return: Position [x, y, z].
        """
        return self.position

    def run(self) -> None:
        """
        Runs the attack.
        :return: None
        """
        self.progress = 0
        self.running = True
        self.a_log.create_file()
        self.a_log.log('Starting attack...')
        self.marlin.set_fan_speed(min(int(self.attack.cooling * 255), 255))
        positions = compute_positions(self.attack.start_pos, self.attack.end_pos, self.attack.step_size)
        self.attack.init()
        self.__move_to_start()
        for i, pos in enumerate(positions):
            self.marlin.move(*pos, 100)
            self.position = pos
            for j in range(self.attack.repetitions):
                self.progress = (i + j) / (len(positions) * self.attack.repetitions)
                if not self.running:
                    return
                self.attack.reset_target()
                self.attack.shout()
                if self.attack.was_successful():
                    self.log.critical('Successful at ' + str(pos))
                    self.a_log.log('Successful at ' + str(pos))
                else:
                    self.a_log.log('Unsuccessful at ' + str(pos))
                if not self.attack.critical_check():
                    self.log.critical('Critical attack check failed.')
                    return
                if not self.__check_temp():
                    time.sleep(20)
        self.attack.shutdown()
        self.a_log.log('Stopping attack...')
        self.a_log.close()

    def stop(self) -> None:
        """
        Stops a running attack.
        :return: None
        """
        self.running = False

    def __move_to_start(self) -> None:
        """
        Homes each axis and moves to the first attack position.
        :return: None
        """
        self.marlin.home(z=True)
        self.marlin.home(x=True, y=True, z=False)
        self.marlin.move(x=self.attack.start_pos[0])
        self.marlin.move(y=self.attack.start_pos[1])
        self.marlin.move(z=self.attack.start_pos[2])

    def __check_temp(self) -> bool:
        """
        Retrieves target temperature and checks if it is too high.
        :return: False if target temperature is to high.
        """
        temp = self.thermal_cam.get_last_temperature()
        if temp > self.attack.max_target_temp:
            self.log.critical('Target temperature too high: {}'.format(temp))
            return False
        else:
            return True
