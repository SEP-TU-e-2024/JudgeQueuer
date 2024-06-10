import socket
import threading

from ..custom_logger import main_logger
from . import Connection
from .judge import Commands, JudgeProtocol

logger = main_logger.getChild("judge_protocol_handler")


def handle_connection(connection: Connection):
    # Instantiate the protocol
    protocol = JudgeProtocol(connection)

    try:
        # Check if the runner is initialized correctly.
        protocol.send_command(Commands.CHECK, True)

        # TODO: While loop that creates commands depending on the requests sent by the Backend

    except Exception:
        logger.error(
            f"An unexpected error has occured while trying to send a command to the runner at {connection.ip}:{connection.port}.",
            exc_info=1,
        )


def establish_connection(host, port):
    # Define the socket and bind it to the given host and port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))

    # Allow the socket to be reused after the program exits without waiting for the default timeout
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.listen(1000)

    logger.info(f"Started listening for Runner connections on {host}:{port}...")

    while True:
        client_sock, addr = sock.accept()
        logger.info(f"Received connection attempt from {addr[0]}:{addr[1]}.")
        handle_connection(Connection(addr[0], addr[1], client_sock, threading.Lock()))

def start_handler(host, port):
    thread = threading.Thread(target=establish_connection, args=(host, port), daemon=True)
    thread.start()
