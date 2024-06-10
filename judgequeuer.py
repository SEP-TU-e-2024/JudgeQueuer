import asyncio
import os
import socket
import threading

from dotenv import load_dotenv

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from models import JudgeRequest, MachineType, ResourceSpecification, Submission
from protocol import Connection
from protocol.judge import JudgeProtocol, Commands

# Initialize environment variables from the `.env` file
load_dotenv()

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)

HOST = "localhost"
PORT = 12345


def handle_conneciton(connection: Connection):
    protocol = JudgeProtocol(connection)
    
    protocol.send_command(Commands.CHECK, True)


def estabish_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen(1000)

    while True:
        client_sock, addr = sock.accept()
        handle_conneciton(Connection(addr[0], addr[1], client_sock, threading.Lock()))


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
    print("Submitting judge request...")
    print(await ae.submit(judge_request))

    # Assign Judge request
    judge_request = JudgeRequest(submission, resource_allocation)

    # Test out submitting judge request
    print("Submitting judge request...")
    print(await ae.submit(judge_request))


if __name__ == "__main__":
    # Wrap main to make sure all Azure objects are closed properly
    async def wrap_main():
        try:
            await main()
        finally:
            await azure.close()

    # Run the main wrapper async
    asyncio.run(wrap_main())

    # Run the main wrapper async
    asyncio.run(wrap_main())
