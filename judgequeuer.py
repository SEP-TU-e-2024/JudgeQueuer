import asyncio
import os

from dotenv import load_dotenv

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from custom_logger import main_logger
from models import JudgeRequest, MachineType, ResourceSpecification, Submission
from protocol import judge_protocol_handler

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


async def main():
    judge_protocol_handler.start_handler()
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
