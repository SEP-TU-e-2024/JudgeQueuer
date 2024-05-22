import json
from typing import List

from azure.core.polling import AsyncLROPoller
from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.mgmt.compute.models import (
	VirtualMachineScaleSet,
	VirtualMachineScaleSetVM,
	VirtualMachineScaleSetVMInstanceIDs,
)
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.resource.resources.aio import ResourceManagementClient

DEFAULT_LOCATION = "UK South"
VMSS_NAME = "my-vmss"


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

	async def list_skus(self, resource_type, location=DEFAULT_LOCATION):
		"""
		List all SKUs of the given resource type (e.g. 'disks' or 'virtualMachines').
		"""
		# TODO see https://github.com/SEP-TU-e-2024/AzureVMSS-tests/issues/4
		# 		listing method is inefficient

		# Uses set to filter out duplicate SKU names
		skus = []
		async for sku in self.compute_client.resource_skus.list(filter=f"location eq '{location}'"):
			if sku.resource_type == resource_type:
				skus.append(sku)
		return list(skus)

	async def list_sku_names(self, resource_type, location=DEFAULT_LOCATION):
		"""
		Lists the names of all SKUs of the given resource type.
		"""
		skus = await self.list_skus(resource_type, location)
		return [sku.name for sku in skus]

	async def list_machine_types(self, location=DEFAULT_LOCATION):
		"""
		Lists all the disk types, such as 'Standard_B1s'.
		"""
		# return await self.list_sku_names('virtualMachines', location)
		return await self.list_sku_names("virtualMachines", location)

	async def list_disk_types(self, location=DEFAULT_LOCATION) -> List["str"]:
		"""
		Lists all the disk types, such as 'StandardSSD_LRS'.
		"""
		return await self.list_sku_names("disks", location)

	async def list_vms(self, vmss_name=VMSS_NAME) -> List[VirtualMachineScaleSetVM]:
		"""
		List the VMs in the set.
		"""
		vms = []

		vm_aiter = self.compute_client.virtual_machine_scale_set_vms.list(
			self.resource_group_name, vmss_name
		)
		async for vm in vm_aiter:
			vms.append(vm)

		return vms

	async def delete_vmss(self, vmss_name=VMSS_NAME):
		"""
		Deletes a VMSS.
		"""
		poller = await self.compute_client.virtual_machine_scale_sets.begin_delete(
			self.resource_group_name, vmss_name
		)

		await poller.wait()

	async def get_vmss(self, name=VMSS_NAME) -> VirtualMachineScaleSet:
		"""
		Gets the Virtual Machine Scale Set instance.
		"""
		return await self.compute_client.virtual_machine_scale_sets.get(self.resource_group_name, name)

	#
	# Modification functions
	#

	async def create_vmss(self, vmss_name=VMSS_NAME, location=DEFAULT_LOCATION):
		"""
		Creates a VMSS.
		"""
		with open("vmss_template.json", "r") as template_file:
			params = json.load(template_file)
		
		# TODO: add params to function, improve parameter construction (e.g. IDs)
		# All parameters
		location = location
		sku = {
			"name": "Standard_B1s",
			"tier": "Standard",
			"capacity": 0
		}
		computer_name_prefix = "my-vmssnu"
		admin_username = "azureuser"
		ssh_key_data = ""

		image = {
			"publisher": "canonical",
			"offer": "0001-com-ubuntu-server-jammy",
			"sku": "22_04-lts-gen2",
			"version": "latest"
		}
		disk_size = 30
		disk_type = "StandardSSD_LRS"

		nic_name = "SEP-test-VM-vnet-nic01"
		nic_nsg_id = "/subscriptions/f5e3b6a6-eff0-49d0-911a-b4272870801d/resourceGroups/VMSS-test-repo/providers/Microsoft.Network/networkSecurityGroups/basicNsgSEP-test-VM-vnet-nic01"
		nic_ip_name = "SEP-test-VM-vnet-nic01-defaultIpConfiguration"
		nic_ip_subnet_id = "/subscriptions/f5e3b6a6-eff0-49d0-911a-b4272870801d/resourceGroups/SEP-tests/providers/Microsoft.Network/virtualNetworks/SEP-test-VM-vnet/subnets/default"
		nic_ip_public_name = "publicIp-SEP-test-VM-vnet-nic01"


		# Fill parameters in template
		params["location"] = location
		params["sku"] = sku
		
		vm_profile = params["properties"]["virtualMachineProfile"]
		os_profile = vm_profile["osProfile"]
		storage_profile = vm_profile["storageProfile"]
		nic_config = vm_profile["networkProfile"]["networkInterfaceConfigurations"][0]
		nic_ip_config = nic_config["properties"]["ipConfigurations"][0]
		
		os_profile["computerNamePrefix"] = computer_name_prefix
		os_profile["adminUsername"] = admin_username
		os_profile["linuxConfiguration"]["ssh"]["publicKeys"][0]["path"] = f"/home/{admin_username}/.ssh/authorized_keys"
		os_profile["linuxConfiguration"]["ssh"]["publicKeys"][0]["keyData"] = ssh_key_data

		storage_profile["imageReference"] = image
		storage_profile["osDisk"]["diskSizeGB"] = disk_size
		storage_profile["osDisk"]["managedDisk"]["storageAccountType"] = disk_type

		nic_config["name"] = nic_name
		nic_config["properties"]["networkSecurityGroup"]["id"] = nic_nsg_id
		nic_ip_config["name"] = nic_ip_name
		nic_ip_config["properties"]["subnet"]["id"] = nic_ip_subnet_id
		nic_ip_config["properties"]["publicIPAddressConfiguration"]["name"] = nic_ip_public_name

		poller: AsyncLROPoller = await self.compute_client.virtual_machine_scale_sets.begin_create_or_update(self.resource_group_name, vmss_name, params)

		await poller.wait()

	async def set_capacity(self, capacity: int, vmss_name=VMSS_NAME):
		"""
		Sets the capacity of the Virtual Machine Scale Set (the amount of instances).

		May delete any machine in the set when decreasing capacity.
		"""
		vmss = await self.get_vmss(vmss_name)
		vmss.sku.capacity = capacity

		poller: AsyncLROPoller = await self.compute_client.virtual_machine_scale_sets.begin_update(
			self.resource_group_name, VMSS_NAME, vmss
		)
		await poller.wait()

	async def delete_vm(self, vm_name: str):
		"""
		Deletes a specific VM from the set.

		Also updates the capacity accordingly.
		"""
		ids = VirtualMachineScaleSetVMInstanceIDs(instance_ids=[vm_name])
		poller = await self.compute_client.virtual_machine_scale_sets.begin_delete_instances(
			self.resource_group_name, VMSS_NAME, ids
		)
		await poller.wait()

	async def close(self):
		"""
		Closes all associated resources.

		Do not use this object after closing.
		"""
		await self.compute_client.close()
		await self.network_client.close()
		await self.resource_client.close()
		await self.credentials.close()
