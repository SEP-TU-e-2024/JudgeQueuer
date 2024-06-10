import asyncio
import os
import socket
import threading

from dotenv import load_dotenv

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from custom_logger import main_logger
from models import JudgeRequest, MachineType, ResourceSpecification, Submission
from protocol import Connection
from protocol.judge import Commands, JudgeProtocol

# Initialize environment variables from the `.env` file
load_dotenv()

# Initialize the logger
logger = main_logger.getChild("JudgeQueuer")

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)

HOST = "localhost"
PORT = 12345


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


def estabish_connection():
    # Define the socket and bind it to the given host and port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))

    # Allow the socket to be reused after the program exits without waiting for the default timeout
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.listen(1000)

    logger.info(f"Started listening for Runner connections on {HOST}:{PORT}...")

    while True:
        client_sock, addr = sock.accept()
        logger.info(f"Received connection attempt from {addr[0]}:{addr[1]}.")
        handle_connection(Connection(addr[0], addr[1], client_sock, threading.Lock()))


async def main():
    threading.Thread(target=estabish_connection, daemon=True).start()
    ae = AzureEvaluator(azure)

    # Assign temporary values

    # Assign submission information
    submission = Submission(1, "source_url")

    # Assign Machine type
    machine_type = MachineType("Standard_B1s", "Standard")
    # machine_type = MachineType("Standard_D2s_v3", "Standard")
    # machine_type = MachineType("Standard_D4s_v3", "Standard")

    # Assign resource specification
    resource_allocation = ResourceSpecification(4, 32, 1, machine_type)

    # Assign Judge request
    judge_request = JudgeRequest(submission, resource_allocation)

    # Test out submitting judge request
    logger.info("Submitting judge request...")
    logger.info(await ae.submit(judge_request))


if __name__ == "__main__":
    # Wrap main to make sure all Azure objects are closed properly
    async def wrap_main():
        try:
            await main()
        finally:
            await azure.close()

    # Run the main wrapper async
    asyncio.run(wrap_main())
