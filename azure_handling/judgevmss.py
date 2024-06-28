import asyncio
import os
import threading

from azure.mgmt.compute.models import (
    VirtualMachineScaleSet,
    VirtualMachineScaleSetVM,
)

from azurewrap import Azure
from custom_logger import main_logger
from models import JudgeRequest, JudgeResult, MachineType
from protocol.judge_protocol_handler import (
    is_machine_name_connected,
)

from .judgevm import JudgeVM

# Initialize the logger
logger = main_logger.getChild("azureevaluator")

# Initialize the logger
logger = main_logger.getChild("azureevaluator")

# Load Azure constants from env vars
NSG_NAME = os.getenv("AZURE_NSG_NAME")
VNET_NAME = os.getenv("AZURE_VNET_NAME")
VNET_SUBNET_NAME = os.getenv("AZURE_VNET_SUBNET_NAME")
VMAPP_RESOURCE_GROUP = os.getenv("AZURE_VMAPP_RESOURCE_GROUP")
VMAPP_GALLERY = os.getenv("AZURE_VMAPP_GALLERY")
VMAPP_NAME = os.getenv("AZURE_VMAPP_NAME")
VMAPP_VERSION = os.getenv("AZURE_VMAPP_VERSION")

class JudgeVMSS:
    """
    An Azure Virtual Machine Scale Set. A Set contains a single machine type.
    """
    machine_type: 'MachineType'
    judgevmss_name: str
    judgevm_dict: dict[str, 'JudgeVM']
    vmss: VirtualMachineScaleSet
    azure: Azure
    capacity_lock: threading.Lock
    submission_lock : threading.Lock
    id: int

    def __init__(self, machine_type: MachineType, judgevmss_name: str, vmss: VirtualMachineScaleSet , azure: Azure):
        self.machine_type = machine_type
        self.judgevmss_name = judgevmss_name
        self.judgevm_dict = {}
        self.vmss = vmss
        self.azure = azure
        self.capacity_lock = threading.Lock()
        self.submission_lock = threading.Lock()
        self.id = 0

    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Handle the request for this machine type vmss, an available vm will be found/created and assigned.
        """

        # Get a right vm that is available
        # TODO: Does this need a lock?
        vm = await self.check_available_vm(judge_request.cpus, judge_request.memory)

        # If no available vm than add capacity
        if vm is None:
            logger.info("No VM available, increasing capacity...")
            # Get available vm after the added capacity, error if no available
            with self.capacity_lock:
                await self.add_capacity()
                vm = await self.check_available_vm(judge_request.cpus, judge_request.memory)

            if vm is None:
                raise Exception("No vm available for judge request, even after adding capacity")

        # Submit using the vm the judge request
        with self.submission_lock:
            judgevm = self.judgevm_dict[vm.name]
        judge_result = await judgevm.submit(judge_request)

        # Downsize capacity if low usage
        if not judgevm.is_busy() and os.getenv("NO_DOWN_SIZING", "False") != "True":
            with self.capacity_lock:
                logger.info(f"Deleting VM {vm.name} because it is idle")
                # TODO make sure this doesnt give concurrency issues
                await self.azure.delete_vm(vm.name, vmss_name=self.vmss.name, block=False)
       
        #Let callback function know they can return the value
        with judge_request.fulfilled:
            judge_request.result = judge_result
            judge_request.fulfilled.notifyAll()

        return judge_result

    async def add_capacity(self):
        """
        Increases capacity of vmss using Azure which could increase the amount of vmss.
        """
        # Increase capacity of vmss with 1 capacity
        capacity = self.vmss.sku.capacity
        await self.azure.set_capacity(capacity + 1, self.judgevmss_name)
        
        # Update judgevm_dict, vm(s) could have been added
        await self.__update_vm_dict()

    async def check_available_vm(self, cpus: int, memory: int) -> VirtualMachineScaleSetVM | None:
        """
        Goes through list of vms in this vmss and checks whether they have enough capacity to take on the resource allocation.
        Returns a vm with enough capacity or None if there is none.
        """

        # Update vm_dict, make sure the dict is up to date
        await self.__update_vm_dict()

        # Get the azure vm class instance associated to the vm
        for vm_name in self.judgevm_dict:
            judgevm = self.judgevm_dict[vm_name]
        
            # Check if there is enough free resource capacity on this vm
            if await judgevm.check_capacity(cpus, memory):
                return judgevm.vm
            
        # No vm found
        return None
    
    async def __update_vm_dict(self):
        """
        Internal method to update the vm_dict,
        checks whether vm is missing from dict and if vm is included when it has already been deleted
        """
        vms = await self.azure.list_vms(self.judgevmss_name)

        for vm in vms:
            # Check if each vm has a judgevm class stored to it in dict
            if vm.name not in self.judgevm_dict:
                avm = await self.azure.get_vm(vm.name)
                machine_name = avm.os_profile.computer_name

                if not is_machine_name_connected(machine_name):
                    logger.info(f"Waiting for VM {vm.name} with machine name {machine_name} to connect")

                    # TODO: notification from judge protocol handler instead of polling
                    while not is_machine_name_connected(machine_name):
                        logger.info(f"Still Waiting for VM {vm.name} with machine name {machine_name} to connect")
                        await asyncio.sleep(1)
                        # TODO: implement timeout

                cpus, memory = await self.azure.get_vm_size(vm.name)
                
                # Create and safe vm class
                judgevm = JudgeVM(vm, machine_name, self.azure, cpus, memory)
                self.judgevm_dict[vm.name] = judgevm

        for key in list(self.judgevm_dict):
            judgevm = self.judgevm_dict[key]
            # Check if the vms in the dictionary are still alive
            if not await judgevm.alive():
                logger.info(f"Deleting VM {key} because it is no longer alive")
                # Remove judgevm from dictionary
                self.judgevm_dict.pop(key)
                # Delete the VM
                #TODO: Reenable, this is not meant to be committed
                # await self.azure.delete_vm(key, self.judgevmss_name, block=False)

    async def is_empty(self) -> bool:
        """
        Check if there are no vms part of this vmss
        """
        await self.__update_vm_dict()
        if len(self.judgevm_dict) > 0:
            # Not empty
            return False
        return True

    async def close(self):
        """
        Close the vmss and check if no associated vms
        """
        if self.is_empty():
            raise Exception("judgevmSS was tried to be closed while having associated vms in dict")

        await self.azure.delete_vmss(self.machine_type)
