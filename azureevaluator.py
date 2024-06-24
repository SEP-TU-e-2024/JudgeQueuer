import asyncio
import os

from azure.mgmt.compute.models import (
    VirtualMachineScaleSet,
    VirtualMachineScaleSetVM,
)

from azurewrap import Azure
from custom_logger import main_logger
from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult, MachineType
from protocol.judge.commands import CheckCommand, StartCommand
from protocol.judge_protocol_handler import (
    get_protocol_from_machine_name,
    is_machine_name_connected,
)

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

instance = None
"""
Keep track of the instance of the AzureEvaluator class, for access in Command classes.
"""
def get_instance() -> 'AzureEvaluator':
    """
    Get the instance of the AzureEvaluator class.
    """
    if instance is None:
        raise Exception("AzureEvaluator instance is not initialized")

    return instance

class AzureEvaluator(SubmissionEvaluator):
    """
    An evaluator using Azure Virtual Machine Scale Set.
    """
    judgevmss_dict: dict['MachineType', 'JudgeVMSS']
    azure: Azure
    
    def __init__(self, azure: Azure):
        self.judgevmss_dict = {}
        self.azure = azure

        # Update the global instance variable with this instance
        global instance
        instance = self

    async def initialize(self):
        """
        Initialize the AzureEvaluator, by filling the VMSS cache with the available VMSS's.
        """
        azure_vmsss = await self.azure.list_vmss()
        for azure_vmss in azure_vmsss:
            # Get the name and machine type of the VMSS
            judgevmss_name = azure_vmss.name
            machine_type = MachineType(azure_vmss.sku.name, azure_vmss.sku.tier)

            judge_vmss = JudgeVMSS(machine_type=machine_type, judgevmss_name=judgevmss_name, vmss=azure_vmss, azure=self.azure)

            # Store VMSS in the cache dict
            self.judgevmss_dict[machine_type] = judge_vmss

    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Handles finding, creating and deletion of vmss that is appropriate for this judgeRequest.
        """
        logger.info(f"Starting of submission for judge request {judge_request}")

        # Get the right VMSS, or make one if needed
        machine_type = judge_request.machine_type
        if machine_type in self.judgevmss_dict:
            judgevmss = self.judgevmss_dict[machine_type]
        else:
            judgevmss_name = "benchlab_judge_" + machine_type.name

            logger.info(f"Creating VMSS {judgevmss_name}")

            await self.azure.create_vmss(judgevmss_name,
                machine_type_name=machine_type.name,
                machine_type_tier=machine_type.tier,
                application_resource_group_name=VMAPP_RESOURCE_GROUP,
                application_gallery=VMAPP_GALLERY,
                application_definition=VMAPP_NAME,
                application_version=VMAPP_VERSION,
                nsg_name=NSG_NAME,
                virtual_network_name=VNET_NAME,
                virtual_network_subnet=VNET_SUBNET_NAME
            )

            vmss = await self.azure.get_vmss(judgevmss_name)

            # Create JudgeVMSS and add it to the cache
            judgevmss = JudgeVMSS(machine_type, judgevmss_name, vmss, self.azure)
            self.judgevmss_dict[machine_type] = judgevmss

        # Then forward call to that.
        judge_result = await judgevmss.submit(judge_request)

        return judge_result

class JudgeVMSS:
    """
    An Azure Virtual Machine Scale Set. A Set contains a single machine type.
    """
    machine_type: 'MachineType'
    judgevmss_name: str
    judgevm_dict: dict[str, 'JudgeVM']
    vmss: VirtualMachineScaleSet
    azure: Azure

    def __init__(self, machine_type: MachineType, judgevmss_name: str, vmss: VirtualMachineScaleSet , azure: Azure):
        self.machine_type = machine_type
        self.judgevmss_name = judgevmss_name
        self.judgevm_dict = {}
        self.vmss = vmss
        self.azure = azure

    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Handle the request for this machine type vmss, an available vm will be found/created and assigned.
        """

        # Get a right vm that is available
        vm = await self.check_available_vm(judge_request.cpus, judge_request.memory)

        # If no available vm then add capacity
        if vm is None:
            logger.info("No VM available, increasing capacity...")
            # Get available vm after the added capacity, error if no available
            await self.add_capacity()

            # TODO: if concurrency, this may give issues (between line above and below, other thread may have used new capacity, so it is no longer available)
            vm = await self.check_available_vm(judge_request.cpus, judge_request.memory)

            if vm is None:
                raise Exception("No vm available for judge request, even after adding capacity")

        # Submit using the vm the judge request
        judgevm = self.judgevm_dict[vm.name]
        judge_result = await judgevm.submit(judge_request)

        # Downsize capacity if low usage
        if not judgevm.is_busy() and os.getenv("NO_DOWN_SIZING") != "True":
            logger.info(f"Deleting VM {vm.name} because it is idle")
            # TODO make sure this doesnt give concurrency issues
            await self.azure.delete_vm(vm.name, vmss_name=self.vmss.name, block=False)

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
                await self.azure.delete_vm(key, self.judgevmss_name, block=False)

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

class JudgeVM:
    """
    An Azure Virtual Machine.
    """
    vm: VirtualMachineScaleSetVM
    machine_name: str
    azure: Azure
    free_cpu: int
    free_memory: int
    tasks = []

    def __init__(self, vm: VirtualMachineScaleSetVM, machine_name: str, azure: Azure, cpus: int, memory: int):
        self.vm = vm
        self.machine_name = machine_name
        self.azure = azure
        self.free_cpu = cpus
        self.free_memory = memory

    async def check_capacity(self, cpus: int, memory: int) -> bool:
        """
        Check whether this vm has enough capacity to take on the resource allocation
        """
        # Check cpu, gpu and memory capacity of vm and return true if there is enough capacity
        if self.free_cpu >= cpus and self.free_memory >= memory:
            return True

        return False

    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        # TODO: communicate the judge request to the VM and monitor status
        logger.info(f"Submitting judge request {judge_request} to VM {self.vm.name} / {self.machine_name}")

        protocol = get_protocol_from_machine_name(self.machine_name)

        try:
            self.tasks.append(judge_request)

            command = StartCommand()
            protocol.send_command(command, True,
                                  evaluation_settings=judge_request.evaluation_settings,
                                  benchmark_instances=judge_request.benchmark_instances,
                                  submission_url=judge_request.submission.source_url,
                                  validator_url=judge_request.submission.validator_url)

            if command.success:
                result = command.result

                return JudgeResult.success(result)
            else:
                cause = command.cause

                return JudgeResult.error(cause)
        finally:
            self.tasks.remove(judge_request)

    def is_busy(self):
        return len(self.tasks) > 0

    async def alive(self):
        """
        Checks if the VM is still alive through a health check.
        """
        logger.info(f"Checking health of VM {self.vm.name}")

        try:
            protocol = get_protocol_from_machine_name(self.machine_name)

            protocol.send_command(CheckCommand(), True, timeout=3)

            logger.info(f"VM {self.vm.name} healthy")
            return True
        except Exception:
            logger.error(f"JudgeVM {self.vm.name} is no longer alive", exc_info=1)
            return False
