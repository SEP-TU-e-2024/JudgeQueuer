from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.resource.resources.aio import ResourceManagementClient


class Azure:
	"""
	A manager for Azure clients and credentials.
	"""
	def __init__(self, subscription_id: str, resource_group_name: str):
		self.credentials = DefaultAzureCredential()

		self.compute_client = ComputeManagementClient(self.credentials, subscription_id)
		self.network_client = NetworkManagementClient(self.credentials, subscription_id)
		self.resource_client = ResourceManagementClient(self.credentials, subscription_id)

		self.resource_group_name = resource_group_name
	
	async def close(self):
		"""
		Closes all associated resources.
		
		Do not use this object after closing.
		"""
		await self.compute_client.close()
		await self.network_client.close()
		await self.resource_client.close()
		await self.credentials.close()
