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

from datetime import datetime
from typing import Optional


class AttackLogger:
    """
    Handles attack logging.
    """
    def __init__(self, log_dir: Optional[str]) -> None:
        """
        Initializes variables.
        :param log_dir: Directory to store log files.
        """
        self.attack_name = None
        self.file = None
        self.dir = log_dir

    def log(self, message: str) -> None:
        """
        Writes a line to the log file.
        :param message: Message to be written.
        :return: None
        """
        if self.file is not None:
            self.file.write(message + '\n')

    def set_name(self, name: str) -> None:
        """
        Sets name of attack.
        :param name: Name of the current attack.
        :return: None
        """
        self.attack_name = name

    def create_file(self) -> None:
        """
        Creates a log file.
        :return: None
        """
        if self.file is not None:
            self.file.close()
        now = datetime.now()
        filename = '{}{}.txt'.format(now.strftime("%d.%m.%Y - %H:%M:%S - "), self.attack_name)
        if self.dir is not None:
            self.file = open(self.dir + '/' + filename, 'w')

    def close(self) -> None:
        """
        Closes the current log file.
        :return: None
        """
        if self.file is not None:
            self.file.close()
