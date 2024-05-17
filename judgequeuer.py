import asyncio
import os

from dotenv import load_dotenv

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from models import JudgeRequest, MachineType, ResourceSpecification, Submission, SubmissionType

# Initialize environment variables from the `.env` file
load_dotenv()

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)

async def main():
	ae = AzureEvaluator()

	submission = Submission()
	submission.type = 1
	submission.source_url = "source_url"

	machine_type = MachineType()
	machine_type.descriptor = "machine_type"

	resource_allocation = ResourceSpecification()
	resource_allocation.machine_type = machine_type
	resource_allocation.num_cpus = 4
	resource_allocation.num_memory = 32
	resource_allocation.num_gpu = 1

	judge_request = JudgeRequest()
	judge_request.submission = submission
	judge_request.resource_allocation = resource_allocation

	print(await ae.submit(judge_request))
	pass

if __name__ == "__main__":
	# Wrap main to make sure all Azure objects are closed properly
	async def wrap_main():
		try:
			await main()
		finally:
			await azure.close()
	
	# Run the main wrapper async
	asyncio.run(wrap_main())
