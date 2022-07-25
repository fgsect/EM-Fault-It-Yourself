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

from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer


class Handler(SimpleHTTPRequestHandler):
    """
    Handler implementation to allow other directories
    """
    directory = None

    def __init__(self, *args, **kwargs) -> None:
        try:
            super().__init__(*args, directory=self.directory, **kwargs)
        except BrokenPipeError:
            pass


class WebServer:
    """
    Simple web server.
    """
    def __init__(self, host: str, port: int, directory: str) -> None:
        """
        Initializes the web server.
        :param host: Host name or IP address
        :param port: Port number
        :param directory: Directory path
        """
        Handler.directory = directory
        self.httpd = HTTPServer((host, port), Handler)
        self.thread = Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
