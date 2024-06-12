import socket
import threading

from custom_logger import main_logger

from . import Connection
from .judge import JudgeProtocol
from .judge.commands.info_command import InfoCommand

logger = main_logger.getChild("judge_protocol_handler")

protocol_dict: dict[str, JudgeProtocol] = {}
"""
Stores all protocols by the runner's hostname.
"""

def handle_connection(connection: Connection):
    # Instantiate the protocol
    protocol = JudgeProtocol(connection)

    machine_name = None
    try:
        # Check if the runner is initialized correctly.
        command = InfoCommand()
        protocol.send_command(command, True)
        machine_name = command.machine_name

        protocol_dict[machine_name] = protocol
        logger.info(f"Accepted connection from runner with machine name {machine_name}")


        # TODO: While loop that creates commands depending on the requests sent by the Backend

    except Exception:
        logger.error(
            f"An unexpected error has occured while trying to send a command to the runner at {connection.ip}:{connection.port}.",
            exc_info=1,
        )
    # finally:
    #     if machine_name is not None and machine_name in protocol_dict:
    #         protocol_dict.pop(machine_name)

def establish_connection(host, port):
    # Define the socket and bind it to the given host and port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))

    # Allow the socket to be reused after the program exits without waiting for the default timeout
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.listen(1000)

    logger.info(f"Started listening for Runner connections on {host}:{port}...")

    while True:
        client_sock, addr = sock.accept()
        logger.info(f"Received connection attempt from {addr[0]}:{addr[1]}.")
        handle_connection(Connection(addr[0], addr[1], client_sock, threading.Lock()))

def start_handler(host, port) -> threading.Thread:
    thread = threading.Thread(target=establish_connection, args=(host, port), daemon=True)
    thread.start()

    return thread
