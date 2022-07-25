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

import cv2
import time
import cmapy
import logging
import threading
import numpy as np
from importlib.resources import read_binary

THERMAL_CAMERA_DELAY = 0.5


class ThermalCamera:
    """
    Manages thermal camera. Computes maximum temperature of each image.
    """
    def __init__(self) -> None:
        """
        Initializes variables and thermal camera.
        """
        self.log = logging.getLogger(__name__)
        self.unavailable = read_binary('emfi_station.web', 'cam_unavailable.png')
        self.mlx = None
        self.mlx_shape = (24, 32)
        self.running = False
        self.thread = None
        self.frames = []
        self.last_temperature = 0
        self.__init_cam()

    def __init_cam(self) -> None:
        """
        Imports lib and initializes thermal camera if available.
        :return: None
        """
        try:
            import board
            import adafruit_mlx90640
            import busio
            i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
            self.mlx = adafruit_mlx90640.MLX90640(i2c)
            self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_16_HZ
        except Exception as e:
            self.log.critical('Init failed: ' + str(e))

    def __cv_frame(self) -> bytes:
        """
        Retrieves raw thermal images and converts them to images.
        Computes maximum temperature of each image.
        :return: OpenCV image
        """
        raw_image = np.zeros((24 * 32,))
        try:
            min_temp = 0
            while min_temp == 0:
                self.mlx.getFrame(raw_image)
                min_temp = np.min(raw_image)
            max_temp = np.max(raw_image)
            self.last_temperature = float(max_temp)
            uint_image = self.__temp_to_uint8(raw_image, min_temp, max_temp)
            image = cv2.applyColorMap(uint_image, cmapy.cmap('jet'))
            image = cv2.resize(image, (640, 480), interpolation=cv2.INTER_NEAREST)
            image = cv2.flip(image, 1)
            _, buffer = cv2.imencode('.jpg', image)
            return buffer
        except ValueError or OSError:
            self.log.critical('Could not retrieve raw image.')
            return self.unavailable

    def __temp_to_uint8(self, image: np.ndarray, min_temp: float, max_temp: float) -> np.ndarray:
        """
        Converts raw thermal image to uint8 array.
        :param image: Raw thermal image
        :param min_temp: Minimum temperature
        :param max_temp: Maximum temperature
        :return: Normalized raw image
        """
        f = np.nan_to_num(image)
        norm = np.uint8((f - min_temp) * 255 / (max_temp - min_temp))
        norm.shape = (24, 32)
        return norm

    def __capture_loop(self) -> None:
        """
        Captures thermal images in a loop and stores them in a buffer.
        Should be run as a background thread.
        :return:
        """
        if self.mlx is None:
            return
        while self.running:
            image = self.__cv_frame()
            if len(self.frames) == 5:
                self.frames = self.frames[1:]
            self.frames.append(image)
            time.sleep(THERMAL_CAMERA_DELAY)

    def get_last_frame(self) -> bytes:
        """
        Retrieves last thermal image from the buffer.
        :return: Thermal image
        """
        if len(self.frames) > 0:
            return self.frames[-1]
        else:
            return self.unavailable

    def start(self) -> None:
        """
        Starts capture loop thread.
        :return: None
        """
        self.running = True
        self.thread = threading.Thread(target=self.__capture_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """
        Stops capture loop thread.
        :return: None
        """
        self.running = False
        if self.thread is not None:
            self.thread.join()

    def get_last_temperature(self) -> float:
        """
        Retrieves last measured maximum temperature.
        :return: Temperature
        """
        return self.last_temperature
