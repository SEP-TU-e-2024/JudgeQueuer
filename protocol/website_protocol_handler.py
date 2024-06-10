"""
The main class of the website protocol server. It handles the connection to the website server.
"""

import socket
import threading
from time import sleep

from custom_logger import main_logger

from .protocol import Connection
from .website.website_protocol import WebsiteProtocol

logger = main_logger.getChild("website_protocol_handler")

class ProtocolHandler:
    ip: str
    port: int
    connect_retry_timeout: float
    debug: bool
    threads: list[threading.Thread]
    connection: Connection
    protocol: WebsiteProtocol

    def __init__(self, ip: str, port: int, connect_retry_timeout: float = 5, debug: bool = False):
        self.ip = ip
        self.port = port
        self.connect_retry_timeout = connect_retry_timeout
        self.debug = debug
        self.threads = []

    def start(self):
        """
        Starts the connection to the website server. In case of a unexpected disconnection, it retries to connect.
        """

        logger.info(f"Trying to connect to the website server at {self.ip}:{self.port} ...")

        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.ip, self.port))
                self.connection = Connection(self.ip, self.port, sock, threading.Lock())
                self.protocol = WebsiteProtocol(self.connection)
                self._handle_commands()

            except (ConnectionRefusedError, ConnectionResetError) as e:
                self.connection = None
                logger.info(f"Failed to connect to website server. Retrying in {self.connect_retry_timeout} seconds... ({e})")
                sleep(self.connect_retry_timeout)

            finally:
                self.stop()

    def _handle_commands(self):
        """
        Handles the incoming commands from the website server.
        """

        while True:
            command_id, command_name, command_args = self.protocol.receive_command()
            thread = threading.Thread(
                target=self.protocol.handle_command,
                args=(command_id, command_name, command_args),
                daemon=True,
            )
            thread.start()
            self.threads.append(thread)

    def stop(self):
        """
        Closes the connection to the website server.
        """

        for thread in self.threads:
            thread.join()
        self.threads.clear()
        if self.connection is not None:
            sock = self.connection.sock
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        self.connection = None

def start_handler(host, port):
    protocol_handler = ProtocolHandler(host, port)
    thread = threading.Thread(target=protocol_handler.start, daemon=True)
    thread.start()
