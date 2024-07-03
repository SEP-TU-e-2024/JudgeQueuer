import random

from azurewrap.base import Azure
from mock.mock_vmss import MockVMSS


class MockAzure(Azure):
    vmss = {}
    vms = {}
    def __init__(self):
        pass
    
    async def list_vms(self, vmss_name):
        if vmss_name in self.vms.keys():
            return self.vms[vmss_name]
        else:
            return []
        
    async def delete_vmss(self, vmss_name):
        if vmss_name in self.vmss:
            self.vmss.remove(vmss_name)

    async def get_vmss(self, name):
        if name in self.vmss:
            return self.vmss[name]
        
    async def list_vmss(self):
        return self.vmss.values()
    
    async def get_vm(self, vm_name):
        if vm_name in self.vms:
            return self.vms[vm_name]

    async def get_vm_size(self, vm_name):
        return 8, 1024

    async def create_vmss(
                    self,
        vmss_name,
        location='a/b/c',
        
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
        self.vmss[vmss_name] = MockVMSS('abc', 'legendary')
        self.vmss[vmss_name].name = vmss_name

    async def set_capacity(self, capacity: int, vmss_name):
        vmss = self.vmss[vmss_name]
        vmss.set_capacity(capacity)

    async def delete_vm(self, vm_name: str, vmss_name, block: bool = True):
        self.vms.pop(vm_name)

    async def close(self):
        pass