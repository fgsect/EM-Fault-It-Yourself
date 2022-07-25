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

import sys
import logging
import argparse

from .config import Config
from .emfi_station import EMFIStation


def main():
    config = Config()
    parser = argparse.ArgumentParser(description='EMFI Station - Orchestrate electromagnetic fault injection attacks')
    parser.add_argument('-i', '--host', type=str, help='hostname or ip address')
    parser.add_argument('-p', '--port', type=int, help='http port (websocket port = http port + 1)')
    parser.add_argument('-s', '--simulate', action='store_true', help='simulate connection to Marlin')
    parser.add_argument('-a', '--attack_dir', type=str, help='attack scripts directory')
    parser.add_argument('-l', '--log_dir', type=str, help='log files directory')
    parser.add_argument('--marlin', type=tuple[str, str], help='(vendor_id, product_id) of Marlin board')
    parser.add_argument('--cal_cam', type=tuple[str, str], help='(vendor_id, product_id) of calibration camera')
    parser.add_argument('--pos_cam', type=tuple[str, str], help='(vendor_id, product_id) of positioning camera')
    parser.add_argument('-v', '--verbosity', action='store_true', help='enable info log level')
    args = parser.parse_args()

    if args.host is not None:
        config.host = args.host
    if args.port is not None:
        config.http_port = args.port
    if args.simulate is not True:
        config.simulate = args.simulate
    if args.attack_dir is not None:
        config.attack_dir = args.attack_dir
    if args.log_dir is not None:
        config.log_dir = args.log_dir
    if args.marlin is not None:
        config.marlin = args.marlin
    if args.cal_cam is not None:
        config.calibration_cam = args.cal_cam
    if args.pos_cam is not None:
        config.positioning_cam = args.pos_cam
    if args.verbosity is True:
        level = logging.INFO
    else:
        level = logging.ERROR

    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(filename)s:%(message)s', stream=sys.stdout, level=level)
    EMFIStation(config)


if __name__ == '__main__':
    main()
