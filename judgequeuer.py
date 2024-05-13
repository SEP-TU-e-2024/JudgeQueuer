import asyncio
import os

from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.resource.resources.aio import ResourceManagementClient
from dotenv import load_dotenv

# Initialize environment variables from the `.env` file
load_dotenv()

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

# Initiate Azure credentials & management clients
credentials = DefaultAzureCredential()
compute_client = ComputeManagementClient(credentials, SUBSCRIPTION_ID)
network_client = NetworkManagementClient(credentials, SUBSCRIPTION_ID)
resource_client = ResourceManagementClient(credentials, SUBSCRIPTION_ID)

async def main():
	pass

if __name__ == "__main__":
	async def wrap_main():
		try:
			await main()
		finally:
			await compute_client.close()
			await network_client.close()
			await resource_client.close()
			await credentials.close()
	
	asyncio.run(wrap_main())
