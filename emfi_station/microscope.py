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
import logging
import threading
from numpy import ndarray
from typing import Optional
from importlib.resources import read_binary

from .utils import get_device_fd


class Microscope:
    """
    Manages a microscope camera. Draws crosshairs.
    """
    def __init__(self, product_id: str, vendor_id: str, resolution: Optional[tuple[int, int]]) -> None:
        """
        Initializes variables and logging. Loads unavailable image.
        :param product_id: Product ID of camera
        :param vendor_id: Vendor ID of camera
        :param resolution: Camera resolution
        """
        self.log = logging.getLogger(__name__)
        self.cam = None
        self.unavailable = read_binary('emfi_station.web', 'cam_unavailable.png')
        self.running = False
        self.thread = None
        self.frames = []
        self.color = (0, 255, 255)
        self.thickness = 2
        self.product_id = product_id
        self.vendor_id = vendor_id
        self.resolution = resolution
        self.__init_cam()

    def __init_cam(self) -> None:
        """
        Initializes the camera.
        :return: None
        """
        try:
            video_dev = get_device_fd(self.vendor_id, self.product_id, 'video4linux')
            self.cam = cv2.VideoCapture(video_dev)
            if self.resolution is not None:
                self.__set_resolution(*self.resolution)
        except FileNotFoundError:
            self.log.critical('Camera is not available: {:s}:{:s}'.format(self.vendor_id, self.product_id))

    def __set_resolution(self, width: int, height: int) -> None:
        """
        Sets camera resolution.
        :param width: Image width
        :param height: Image height
        :return: None
        """
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def start(self) -> None:
        """
        Starts the capture loop thread running in the background.
        :return: None
        """
        self.running = True
        self.thread = threading.Thread(target=self.__capture_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """
        Stops the capture loop thread that runs in the background.
        :return: None
        """
        self.running = False
        if self.thread is not None:
            self.thread.join()

    def __capture_loop(self) -> None:
        """
        Retrieves images from the camera in a loop and stores them in a small buffer.
        Should be run as background thread.
        :return: None
        """
        if self.cam is None:
            return
        while self.running:
            success, image = self.cam.read()
            if success:
                image = self.__draw_crosshairs(image)
                if len(self.frames) == 5:
                    self.frames = self.frames[1:]
                self.frames.append(image)

    def get_frame(self) -> bytes:
        """
        Returns last camera image. Reads from image buffer.
        :return: Camera image
        """
        if len(self.frames) > 0:
            return cv2.imencode('.jpg', self.frames[-1])[1].tobytes()
        else:
            return self.unavailable

    def __draw_crosshairs(self, image: ndarray) -> ndarray:
        """
        Draws crosshairs on an image.
        :param image: Image to draw on.
        :return: Image including crosshairs.
        """
        height, width, _ = image.shape
        for i in range(0, int(height / 2), 75):
            image = cv2.circle(image, (int(width / 2), int(height / 2)), i, self.color, self.thickness)
        image = cv2.line(image, (0, int(height / 2)), (width, int(height / 2)), self.color, self.thickness)
        image = cv2.line(image, (int(width / 2), 0), (int(width / 2), height), self.color, self.thickness)
        return image
