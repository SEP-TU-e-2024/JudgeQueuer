"""
The main class of the website protocol server. It handles the connection to the website server.
"""

import asyncio
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

    def __init__(self, ip: str, port: int, connect_retry_timeout: float = 20, debug: bool = False):
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

            thread = self._run_future_off_thread(
                self.protocol.handle_command(command_id, command_name, command_args)
            )

            self.threads.append(thread)

    def _run_future_off_thread(self, future) -> threading.Thread:
        """
        Runs the given future in a separate thread, returning the thread object.
        """
        # Entrypoint for command execution thread, sets event loop and runs with the future until completion
        def run_event_loop(loop: asyncio.AbstractEventLoop, future):
            asyncio.set_event_loop(loop)
            loop.run_until_complete(future)

        # Create a new event loop
        new_loop = asyncio.new_event_loop()

        # Start the event loop in a new thread, starting the command handling future
        thread = threading.Thread(target=run_event_loop,
                                    args=(new_loop, future),
                                    daemon=True)
        thread.start()

        return thread

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

def start_handler(host, port) -> threading.Thread:
    protocol_handler = ProtocolHandler(host, port)
    thread = threading.Thread(target=protocol_handler.start, daemon=True)
    thread.start()

    return thread