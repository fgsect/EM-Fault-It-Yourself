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
import asyncio
import logging
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError

from .config import Config
from .websocket_helper import WebSocketHelper


class WebSocketServer:
    """
    Web socket server. The entire communication to the web interface is done through
    this web socket including the camera streams.
    """

    def __init__(self, config: Config):
        """
        Initializes variables
        :param config: Configuration object.
        """
        self.log = logging.getLogger(__name__)
        self.host = config.host
        self.port = config.http_port + 1
        self.connected = set()
        self.loop = None
        self.stop = None
        self.helper = WebSocketHelper(config)

    async def __send_state_update(self, websocket: websockets.WebSocketServerProtocol = None) -> None:
        """
        Sends state update to one or all clients.
        :param websocket: Client to send state update to.
        :return: None
        """
        state = self.helper.get_state_json()
        if websocket is None:
            websockets.broadcast(self.connected, state)
        else:
            await websocket.send(state)

    async def __send_error(self, websocket: websockets.WebSocketServerProtocol, message: str) -> None:
        """
        Sends an error message to a client.
        :param websocket: Client to send message to.
        :param message: Message to send.
        :return: None
        """
        msg = json.dumps({'type': 'error', 'message': message})
        await websocket.send(msg)

    async def __message_handler(self, message: str, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Handles all incoming message from every client.
        :param message: Incoming websocket message.
        :param websocket: Client that sent the message.
        :return: None
        """
        msg = json.loads(message)
        self.log.debug(msg)

        if msg['type'] == 'command':
            cmd = msg['cmd']

            # check if another operation is still running
            if self.helper.is_running() and cmd != 'disableJoystick' and cmd != 'stopAttack':
                await self.__send_error(websocket, 'Please wait until the previous action terminates.')
                return

            try:
                success = False
                if cmd == 'enableJoystick':
                    success = self.helper.enable_joystick(float(msg['speed']), float(msg['step']))
                elif cmd == 'disableJoystick':
                    success = self.helper.disable_joystick()
                elif cmd == 'step':
                    success = self.helper.step(float(msg['speed']), float(msg['x']), float(msg['y']), float(msg['z']))
                elif cmd == 'home':
                    success = self.helper.home(bool(msg['x']), bool(msg['y']), bool(msg['z']))
                elif cmd == 'move':
                    success = self.helper.move(float(msg['speed']), float(msg['x']), float(msg['y']), float(msg['z']))
                elif cmd == 'startAttack':
                    success = self.helper.start_attack(msg['name'])
                elif cmd == 'stopAttack':
                    success = self.helper.stop_attack()
                elif cmd == 'safeZ':
                    success = self.helper.set_safe_z(msg['z'])
                if not success:
                    await self.__send_error(websocket, 'An error occurred. Please check the logs.')
            except ValueError:
                await self.__send_error(websocket, 'Please provide valid values.')

            await self.__send_state_update()

    async def __microscope_producer(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Sends microscope images to a client every 100ms.
        :param websocket: Client to send image to.
        :return: None
        """
        while True:
            image = self.helper.get_microscope_frame()
            message = json.dumps({'type': 'microscope', 'image': image})
            await websocket.send(message)
            await asyncio.sleep(0.05)

    async def __calibration_producer(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Sends microscope images to a client every 100ms.
        :param websocket: Client to send image to.
        :return: None
        """
        while True:
            image = self.helper.get_calibration_frame()
            message = json.dumps({'type': 'calibration', 'image': image})
            await websocket.send(message)
            await asyncio.sleep(0.05)

    async def __thermal_camera_producer(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Sends thermal images to a client every 0.5s.
        :param websocket: Client to send image to.
        :return: None
        """
        while True:
            image = self.helper.get_thermal_frame()
            message = json.dumps({'type': 'thermal_camera', 'image': image})
            await websocket.send(message)
            await asyncio.sleep(0.5)

    async def __state_producer(self) -> None:
        """
        Broadcasts state update every second.
        :return: None
        """
        while True:
            await self.__send_state_update()
            await asyncio.sleep(1)

    async def __consumer(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Forwards all incoming messages.
        :param websocket: Client that sent the message.
        :return: None
        """
        async for message in websocket:
            await self.__message_handler(message, websocket)

    def __on_first_connected(self) -> None:
        """
        Called on when the first client is connected.
        :return: None
        """
        self.helper.on_first_connected()

    def __on_last_disconnected(self) -> None:
        """
        Called when last client is disconnected.
        :return: None
        """
        self.helper.on_last_disconnected()

    async def __connection_handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Called when client connects to the server.
        :param websocket: Client that connects.
        :return: None
        """
        if len(self.connected) == 0:
            self.__on_first_connected()

        self.connected.add(websocket)
        await self.__send_state_update(websocket)
        try:
            await asyncio.gather(
                self.__consumer(websocket),
                self.__thermal_camera_producer(websocket),
                self.__microscope_producer(websocket),
                self.__calibration_producer(websocket),
                self.__state_producer(),
            )
        except ConnectionClosed or ConnectionClosedOK or ConnectionClosedError:
            pass
        finally:
            self.connected.remove(websocket)
            if len(self.connected) == 0:
                self.__on_last_disconnected()

    async def __serve_forever(self) -> None:
        """
        Runs the websocket server.
        :return: None
        """
        async with websockets.serve(self.__connection_handler, self.host, self.port):
            await self.stop

    def shutdown(self) -> None:
        """
        Shuts the websocket server down gracefully.
        :return: None
        """
        self.helper.shutdown()
        if self.stop is not None:
            self.stop.set_result(None)

    def run(self):
        """
        Starts the event loop thread that executes the websocket server.
        :return: None
        """
        self.loop = asyncio.get_event_loop()
        self.stop = self.loop.create_future()
        self.loop.create_task(self.__serve_forever())
        self.loop.run_forever()
