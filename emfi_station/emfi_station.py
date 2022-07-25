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

from .config import Config
from .web_server import WebServer
from .websocket_server import WebSocketServer


class EMFIStation:
    """
    EMFI station base class.
    """
    def __init__(self, config: Config):
        """
        Initialize EMFI station server.
        :param config: Configuration object.
        """
        self.log = logging.getLogger(__name__)
        path = __file__.rsplit('/', 1)[0] + '/web'
        WebServer(config.host, config.http_port, path)
        ws = WebSocketServer(config)
        try:
            ws.run()
        except KeyboardInterrupt:
            self.log.critical('Exiting...')
            ws.shutdown()
            self.log.critical('Bye!')
