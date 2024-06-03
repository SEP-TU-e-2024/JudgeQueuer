import asyncio
import os

from dotenv import load_dotenv

from azureevaluator import AzureEvaluator
from azurewrap import Azure
from models import JudgeRequest, MachineType, ResourceSpecification, Submission

# Initialize environment variables from the `.env` file
load_dotenv()

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)

async def main():
	ae = AzureEvaluator(azure)

	# Assign temporary values
	
	# Assign submission information
	submission = Submission(1, "source_url")

	# Assign Machine type
	machine_type = MachineType("machine_type2")

	# Assign resource specification
	resource_allocation = ResourceSpecification(4, 32, 1, machine_type)

	# Assign Judge request
	judge_request = JudgeRequest(submission, resource_allocation)

	# Test out submitting judge request
	print(await ae.submit(judge_request))

async def main2():
	print('Starting')
	vmss_name = 'mytestvmss_11'

	await azure.create_vmss(vmss_name)
	print('Created VMSS')

	for i in range(1):
		print(f'-- Iteration: {i}')
		try:
			await azure.set_capacity(1, vmss_name)
			print(f'-- Created VM {i} successfully')
		except Exception as e:
			print(f'-- Failed to create VM {i}')
			print(e)

		# await azure.set_capacity(0, vmss_name)

if __name__ == "__main__":
	# Wrap main to make sure all Azure objects are closed properly
	async def wrap_main():
		try:
			await main2()
		finally:
			await azure.close()
	
	# Run the main wrapper async
	asyncio.run(wrap_main())
