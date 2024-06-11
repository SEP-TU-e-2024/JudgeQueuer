import json
from typing import List

from azure.core.credentials_async import AsyncTokenCredential
from azure.core.polling import AsyncLROPoller
from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.mgmt.compute.models import (
    VirtualMachine,
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
    credentials: AsyncTokenCredential
    compute_client: ComputeManagementClient
    network_client: NetworkManagementClient
    resource_client: ResourceManagementClient
    
    resource_group_name: str
    subscription_id: str

    def __init__(self, subscription_id: str, resource_group_name: str):
        self.credentials = DefaultAzureCredential()

        self.compute_client = ComputeManagementClient(self.credentials, subscription_id)
        self.network_client = NetworkManagementClient(self.credentials, subscription_id)
        self.resource_client = ResourceManagementClient(self.credentials, subscription_id)

        self.subscription_id = subscription_id
        self.resource_group_name = resource_group_name

    async def list_skus(self, resource_type, location=DEFAULT_LOCATION):
        """
        List all SKUs of the given resource type (e.g. 'disks' or 'virtualMachines').
        """
        # TODO see https://github.com/SEP-TU-e-2024/AzureVMSS-tests/issues/4
        #         listing method is inefficient

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
        Lists all the machine types, such as 'Standard_B1s'.
        """
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

    async def list_vmss(self) -> list[VirtualMachineScaleSet]:
        """
        List all VMSS's in the resource group.
        """
        vmsss = []
        async for vmss in self.compute_client.virtual_machine_scale_sets.list(self.resource_group_name):
            vmsss.append(vmss)
        return vmsss

    async def get_vm(self, name: str) -> VirtualMachine:
        """
        Gets the Virtual Machine with the given name.
        """
        return await self.compute_client.virtual_machines.get(self.resource_group_name, name)

    #
    # Modification functions
    #

    async def create_vmss(
        self,
        vmss_name,
        location=DEFAULT_LOCATION,
        
        machine_type_name="Standard_B1s",
        machine_type_tier="Standard",
        disk_type="StandardSSD_LRS",
        disk_size=30,
        
        computer_name_prefix="benchlab-judge-runner",
        admin_username="benchlab",
        
        nic_name="benchlab-judge-nic",
        nic_ip_name="benchlab-judge-nic-ip",
        nic_ip_public_name="benchlab-judge-nic-public-ip",

        # TODO: auto generate NSG & virtual network?
        application_resource_group_name="BenchLab123",
        application_gallery="runner_container_gallery123",
        application_definition="runner_container_application123",
        application_version="latest123",
        nsg_name="judge-queuer-nsg123",
        virtual_network_name="judge-queuer-vnet123",
        virtual_network_subnet="default123",
    ):
        """
        Creates a VMSS.
        """
        with open("vmss_template.json", "r") as template_file:
            params = json.load(template_file)

        # Hardware information
        sku = {
            "name": machine_type_name,
            "tier": machine_type_tier,
            "capacity": 0
        }

        # OS related information
        os_image = {
            "publisher": "canonical",
            "offer": "0001-com-ubuntu-server-jammy",
            "sku": "22_04-lts-gen2",
            "version": "latest"
        }
        ssh_key_data = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDDUKfFGpdsPyuxaINX5nNfWKMIR0pjZia8kfcsC6tC27zyLYogLQ5eIEhHXofnExmlfiD6R5rtclYhF3Q33VVaJeVg+KtN/Wx/t4REIiCVsI98wFZUWGnXuq6yuAC3GGfLfIqrOfz1/xKwbk+Swj3u4YIXpfT0yLhCXpwmni178qHn02vkd2BlytOTYcyMFiXCnN9uBA2MNu85LMqqL4hHg+HjOCDOivsTlswGt6kd8kfq04eADGgUCOMy2XQk53iD2PgK0gCQxKQlq/ACHMs5fOUFIT8jpYxXmIqT5Y/p1pEPWS3w37t/wD+QHllPbTvTLkCEksPRQr0RMFUj7Ov8/sAdbh1lBidmShWP7txJyVPby1+SVv/dO7Ghpyl58SYC9Zu1oLy8WCmPNE3aTFqTtHwJiGivI4Ymq/lHLNPUrhzzLU6Ek+SaAqre8rMv6D+Ap7tNDmigQdtkDpxNahhj8vFdKdUR1BtF3TsHa/uQRv111jVULi9Uz89Arjdpc9HvRnhI8x2ecIt7pEAfDfxl5i/GaiD5d0F+c6k8WSh2ZBlXbVHcPlGMwWPaaIVok9ghjV7vWn9xN7kM8SR4axf9HPMnGhFBLJp37JBE1TRynVqlUzDo2vCBvGBbYJ6b9ERnuQMHNNqcAguzkQiHqfWTg8vQ1KmhK7wYD6KwysglNQ== tue\20212025@S20212025"
        # TODO remove hardcoded ssh key

        # Add parameters to template
        params["location"] = location
        params["sku"] = sku

        vm_profile = params["properties"]["virtualMachineProfile"]
        os_profile = vm_profile["osProfile"]
        storage_profile = vm_profile["storageProfile"]
        nic_config = vm_profile["networkProfile"]["networkInterfaceConfigurations"][0]
        nic_ip_config = nic_config["properties"]["ipConfigurations"][0]
        gallery_application = vm_profile["applicationProfile"]["galleryApplications"][0]
        
        os_profile["computerNamePrefix"] = computer_name_prefix
        os_profile["adminUsername"] = admin_username
        os_profile["linuxConfiguration"]["ssh"]["publicKeys"][0]["path"] = f"/home/{admin_username}/.ssh/authorized_keys"
        os_profile["linuxConfiguration"]["ssh"]["publicKeys"][0]["keyData"] = ssh_key_data

        storage_profile["imageReference"] = os_image
        storage_profile["osDisk"]["diskSizeGB"] = disk_size
        storage_profile["osDisk"]["managedDisk"]["storageAccountType"] = disk_type

        nic_config["name"] = nic_name
        nic_config["properties"]["networkSecurityGroup"]["id"] = f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Network/networkSecurityGroups/{nsg_name}"
        nic_ip_config["name"] = nic_ip_name
        nic_ip_config["properties"]["subnet"]["id"] = f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Network/virtualNetworks/{virtual_network_name}/subnets/{virtual_network_subnet}"
        nic_ip_config["properties"]["publicIPAddressConfiguration"]["name"] = nic_ip_public_name

        gallery_application["packageReferenceId"] = f"/subscriptions/{self.subscription_id}/resourceGroups/{application_resource_group_name}/providers/Microsoft.Compute/galleries/{application_gallery}/applications/{application_definition}/versions/{application_version}"

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
            self.resource_group_name, vmss_name, vmss
        )
        await poller.wait()

    async def delete_vm(self, vm_name: str, vmss_name=VMSS_NAME):
        """
        Deletes a specific VM from the set.

        Also updates the capacity accordingly.
        """
        ids = VirtualMachineScaleSetVMInstanceIDs(instance_ids=[vm_name])
        poller = await self.compute_client.virtual_machine_scale_sets.begin_delete_instances(
            self.resource_group_name, vmss_name, ids
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
