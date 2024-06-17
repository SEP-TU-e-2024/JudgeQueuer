#!/usr/bin/env python3.12
from dotenv import load_dotenv

# Initialize environment variables from the `.env` file
# Should be done before any imports, in order to make sure all files with top-level code has env vars available to them
load_dotenv(override=True)

import asyncio
import os

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from custom_logger import main_logger
from models import JudgeRequest, MachineType, ResourceSpecification, Submission
from protocol import judge_protocol_handler, website_protocol_handler

# Initialize the logger
logger = main_logger.getChild("JudgeQueuer")

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

# Initiate Azure objects
azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)
ae = AzureEvaluator(azure)

# Initiate protocol constants
JUDGE_PROTOCOL_HOST = "0.0.0.0"
JUDGE_PROTOCOL_PORT = 12345
WEBSITE_PROTOCOL_HOST = "0.0.0.0"
WEBSITE_PROTOCOL_PORT = 30000


async def main():
    logger.info("Initializer AzureEvaluator...")
    await ae.initialize()

    logger.info("Starting protocols...")

    judge_thread = judge_protocol_handler.start_handler(JUDGE_PROTOCOL_HOST, JUDGE_PROTOCOL_PORT)
    website_thread = website_protocol_handler.start_handler(WEBSITE_PROTOCOL_HOST, WEBSITE_PROTOCOL_PORT)

    logger.info("JudgeQueuer ready")

    # await send_test_submission()

    judge_thread.join()
    website_thread.join()

async def send_test_submission():
    submission = Submission(1, "https://storagebenchlab.blob.core.windows.net/submissions/submission.zip", "https://storagebenchlab.blob.core.windows.net/validators/validator.zip")
    machine_type = MachineType("Standard_B1s", "Standard")
    resource_allocation = ResourceSpecification(num_cpu=1, num_memory=10, num_gpu=0, machine_type=machine_type, time_limit=30)
    judge_request = JudgeRequest(submission, resource_allocation)

    # Test out submitting judge request
    logger.info("Submitting judge request...")
    judge_result = await ae.submit(judge_request)
    logger.info(f"Received VM judge result {judge_result.result}")

if __name__ == "__main__":
    # Wrap main to make sure all Azure objects are closed properly
    async def wrap_main():
        try:
            await main()
        finally:
            await azure.close()

    # Run the main wrapper async
    asyncio.run(wrap_main())
