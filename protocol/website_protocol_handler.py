"""
The main class of the website protocol server. It handles the connection to the website server.
"""

import asyncio
import socket
import threading

from custom_logger import main_logger

from .protocol import Connection
from .website.website_protocol import WebsiteProtocol

logger = main_logger.getChild("website_protocol_handler")


class ProtocolHandler:
    host: str
    port: int
    connect_retry_timeout: float
    debug: bool
    threads: list[threading.Thread]
    connection: Connection
    protocol: WebsiteProtocol

    def __init__(self, host: str, port: int, connect_retry_timeout: float = 5, debug: bool = False):
        self.host = host
        self.port = port
        self.connect_retry_timeout = connect_retry_timeout
        self.debug = debug
        self.threads = []

    def start(self):
        """
        Starts the connection to the website server. In case of a unexpected disconnection, it retries to connect.
        """

        while True:
            try:
                # Define the socket and bind it to the given host and port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Allow the socket to be reused after the program exits without waiting for the default timeout
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                sock.bind((self.host, self.port))
                sock.listen(1)

                logger.info(f"Started listening for the Website connection on {self.host}:{self.port}...")

                client_sock, addr = sock.accept()
                logger.info(f"Received website connection from {addr[0]}:{addr[1]}.")

                self.connection = Connection(addr[0], addr[1], client_sock, threading.Lock())
                self.protocol = WebsiteProtocol(self.connection)
                self._handle_commands()

            except (ConnectionRefusedError, ConnectionResetError) as e:
                self.connection = None
                logger.info(f"Website disconnected! ({e})")

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
        thread = threading.Thread(target=run_event_loop, args=(new_loop, future), daemon=True)
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
