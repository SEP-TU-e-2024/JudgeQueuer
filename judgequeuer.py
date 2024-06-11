import asyncio
import os
from time import sleep

from dotenv import load_dotenv

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from custom_logger import main_logger
from protocol import judge_protocol_handler, website_protocol_handler

# Initialize environment variables from the `.env` file
load_dotenv()

# Initialize the logger
logger = main_logger.getChild("JudgeQueuer")

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

# Initiate Azure objects
azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)
ae = AzureEvaluator(azure)

# Initiate protocol constants
JUDGE_PROTOCOL_HOST = "localhost"
JUDGE_PROTOCOL_PORT = 12345
WEBSITE_PROTOCOL_HOST = "localhost"
WEBSITE_PROTOCOL_PORT = 30000


async def main():
    logger.info("Initializer AzureEvaluator...")
    await ae.initialize()

    logger.info("Starting protocols...")

    judge_protocol_handler.start_handler(JUDGE_PROTOCOL_HOST, JUDGE_PROTOCOL_PORT)
    website_protocol_handler.start_handler(WEBSITE_PROTOCOL_HOST, WEBSITE_PROTOCOL_PORT)

    logger.info("JudgeQueuer ready")

    # TODO TP remove
    sleep(99999999)

if __name__ == "__main__":
    # Wrap main to make sure all Azure objects are closed properly
    async def wrap_main():
        try:
            await main()
        finally:
            await azure.close()

    # Run the main wrapper async
    asyncio.run(wrap_main())
