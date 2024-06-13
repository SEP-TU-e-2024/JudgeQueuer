import socket
import threading

from custom_logger import main_logger

from . import Connection
from .judge import JudgeProtocol
from .judge.commands.info_command import InfoCommand

logger = main_logger.getChild("judge_protocol_handler")

protocol_dict_lock = threading.Lock()
"""
Lock for protocol_dict to prevent simultaneous access.
"""
protocol_dict: dict[str, JudgeProtocol] = {}
"""
Stores all protocols by the runner's hostname.
"""

def is_machine_name_connected(machine_name: str) -> bool:
    with protocol_dict_lock:
        return machine_name in protocol_dict

def get_protocol_from_machine_name(machine_name: str) -> JudgeProtocol:
    with protocol_dict_lock:
        return protocol_dict[machine_name]

def handle_connection(connection: Connection):
    # Instantiate the protocol
    protocol = JudgeProtocol(connection)

    machine_name = None
    try:
        # Request the machine name of the runner
        command = InfoCommand()
        protocol.send_command(command, True)
        machine_name = command.machine_name

        # Store the protocol in the protocol_dict with its machine name
        with protocol_dict_lock:
            if machine_name in protocol_dict:
                raise Exception("Runner with the same machine name is already connected")
            protocol_dict[machine_name] = protocol
        logger.info(f"Accepted connection from runner with machine name {machine_name}")

        # Add close listener to remove the protocol from the protocol_dict when the runner disconnects
        def on_close(machine_name):
            with protocol_dict_lock:
                protocol_dict.pop(machine_name)
                logger.info(f"Runner with machine name {machine_name} has disconnected")

        protocol.set_close_listener(on_close, (machine_name,))
    except Exception:
        logger.error(
            f"An unexpected error has occured while trying to send a command to the runner at {connection.ip}:{connection.port}.",
            exc_info=1,
        )

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

        connection = Connection(addr[0], addr[1], client_sock, threading.Lock())
        handle_connection(connection)

def start_handler(host, port) -> threading.Thread:
    thread = threading.Thread(target=establish_connection, args=(host, port), daemon=True)
    thread.start()

    return thread
