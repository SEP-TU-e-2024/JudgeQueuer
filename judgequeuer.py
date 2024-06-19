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
from models import JudgeRequest, MachineType, Submission
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
    evaluation_settings = {
        "cpu":1,
		"time_limit":60.0,
		"memory":256,
		"machine_type":"Standard_B1s"
	}
    benchmark_instancs = {
        '0a800b64-0cce-4cb2-95ab-39a5064ece4e': 'https://storagebenchlab.blob.core.windows.net/benchmark-instances-test-validator/instance2.txt',
        '83a8977e-760a-4d44-9a67-e07ca4d4c155': 'https://storagebenchlab.blob.core.windows.net/benchmark-instances-test-validator/instance1.txt'
    }
    judge_request = JudgeRequest(submission, machine_type, cpus=1, memory=256, evaluation_settings=evaluation_settings, benchmark_instances=benchmark_instancs)

    # Test out submitting judge request
    logger.info("Submitting judge request...")
    judge_result = await ae.submit(judge_request)
    logger.info(f"Received VM judge result {judge_result}")

if __name__ == "__main__":
    # Wrap main to make sure all Azure objects are closed properly
    async def wrap_main():
        try:
            await main()
        finally:
            await azure.close()

    # Run the main wrapper async
    asyncio.run(wrap_main())
