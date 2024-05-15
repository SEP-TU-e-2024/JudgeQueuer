import asyncio
import os

from dotenv import load_dotenv

from azurewrap import Azure

# Initialize environment variables from the `.env` file
load_dotenv()

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

azure = Azure(SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)

async def main():
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
