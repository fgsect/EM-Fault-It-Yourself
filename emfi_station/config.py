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

class Config:
    """
    Encapsulates configuration variables
    """
    host: str = 'localhost'
    http_port: int = 9118
    simulate: bool = True
    attack_dir: str = None
    log_dir: str = None
    positioning_cam: tuple[str, str] = ('299f', 'eb1a')
    calibration_cam: tuple[str, str] = ('6353', '0c45')
    marlin: tuple[str, str] = ('0483', '5740')
