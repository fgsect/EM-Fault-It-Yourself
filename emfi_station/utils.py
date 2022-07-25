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

import pyudev

# ChipShouter vendor=0403 model=6015 subsystem=tty
# SKR Pro vendor=0483 model=5740 subsystem=tty
# Microscope vendor=eb1a model=299f subsystem=video4linux
# Joystick vendor=046d model=c214 subsystem=input
# Thermal Camera I2C


def get_device_fd(vendor: str, product: str, subsystem: str) -> str:
    """
    Returns device file path.
    :param vendor: Vendor ID
    :param product: Product ID
    :param subsystem: Subsystem name (e.g.: 'video4linux', 'input' or 'tty')
    :return: File path
    """
    context = pyudev.Context()
    for device in context.list_devices(subsystem=subsystem):
        try:
            if device.properties['ID_VENDOR_ID'] == vendor and \
               device.properties['ID_MODEL_ID'] == product:
                return device.properties['DEVNAME']
        except KeyError:
            pass
    raise FileNotFoundError('Device was not found.')


def get_decimals_len(numbers: list[float]) -> int:
    """
    Find maximum number of decimals in a lust of floats.
    :param numbers: List of floats
    :return: Maximum number of decimals
    """
    fp = 0
    for x in numbers:
        try:
            decs = len(str(x).split('.')[1])
            if decs > fp:
                fp = decs
        except IndexError:
            pass
    return fp


def range_rounded(start: float, stop: float, step: float) -> list[float]:
    """
    Range from start to stop with rounded values.
    :param start: Start value
    :param stop: Stop value
    :param step: Step size
    :return: List of floats
    """
    fp = get_decimals_len([start, stop, step])
    lst = []
    if start < stop:
        while start < stop:
            lst.append(round(start, fp))
            start += step
    else:
        while start > stop:
            lst.append(round(start, fp))
            start -= step
    lst.append(round(stop, fp))
    return lst


def compute_positions(start: list[float, float, float], stop: list[float, float, float], step: float):
    """
    Returns a list of positions between start position and stop position.
    List is ordered to have the lowest trip length.
    :param start: Start position
    :param stop: Stop position
    :param step: Step size
    :return: Ordered list of positions
    """
    fp = get_decimals_len([start, stop, step])
    positions = []
    x_pos = range_rounded(start[0], stop[0], step)
    y_pos = range_rounded(start[1], stop[1], step)
    z_pos = range_rounded(start[2], stop[2], step)
    for z in z_pos:
        for x in x_pos:
            for y in y_pos:
                positions.append((x, y, z))
            y_pos.reverse()
        x_pos.reverse()

    # validate positions
    for pos in positions:
        for i in pos:
            try:
                pl = len(str(i).split('.')[1])
                assert pl <= fp
            except IndexError:
                pass

    return positions
