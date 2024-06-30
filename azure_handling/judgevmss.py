import asyncio
import os
import queue
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
    submission_queue: queue.Queue[JudgeRequest]
    dormant_vms: queue.Queue[JudgeVM]

    def __init__(self, machine_type: MachineType, judgevmss_name: str, vmss: VirtualMachineScaleSet , azure: Azure):
        self.machine_type = machine_type
        self.judgevmss_name = judgevmss_name
        self.judgevm_dict = {}
        self.vmss = vmss
        self.azure = azure
        self.capacity_lock = threading.Lock()
        self.submission_lock = threading.Lock()
        self.id = 0
        self.submission_queue = queue.Queue()
        self.dormant_vms = queue.Queue()

        threading.Thread(target=asyncio.run, args=[self.request_handler()], daemon=True).start()

    async def request_handler(self):
        logger.info(f'VMSS #{self.id}: Request handling thread succesfully started')
        await self.__update_vm_dict()
        while True:
            #Check whether the queue is empty
            if self.submission_queue.empty():
                #If so, sleep for one second so we don't overload
                # await self.__update_vm_dict()
                await asyncio.sleep(1)
                continue
            else:
                #There is a new request to handle
                request = self.submission_queue.get()
                assert type(request) == JudgeRequest

                logger.info(f"VMSS #{self.id} handling new request: #{request.id}")

                assigned = False
                for vm_name in self.judgevm_dict:
                    judgevm = self.judgevm_dict[vm_name]

                    if await judgevm.check_capacity(request.cpus, request.memory) or judgevm.check_idle_queue():
                        # We have an available VM
                        threading.Thread(target=asyncio.run, args=[self.submit_request_to_vm(request, judgevm)], daemon=True).start()
                        assigned = True
                
                for judgevm in self.dormant_vms.queue:
                    assert type(judgevm) == JudgeVM
                    logger.info(f'JudgeVM {judgevm.id} capacity: {judgevm.free_cpu} cpu, {judgevm.free_memory} memory')
                    if await judgevm.check_capacity(request.cpus, request.memory) or judgevm.check_idle_queue():
                        #Assign it to a dormant vm with enough space
                        threading.Thread(target=asyncio.run, args=[self.submit_request_to_vm(request, judgevm)], daemon=True).start()
                        assigned = True

                if not assigned:
                    #We need to create a new VM
                    judgevm = JudgeVM(None, None, self.azure, request.cpus, request.memory, True)
                    self.dormant_vms.put(judgevm)
                    #TODO: Add this to VM Dict somehow, so new requests can be assigned to dormant vms too
                    threading.Thread(target=asyncio.run, args=[self.submit_request_to_vm(request,judgevm)], daemon=True).start()
                    threading.Thread(target=asyncio.run, args=[self.add_capacity()],daemon=True).start()



    async def add_capacity_and_submit_to_vm(self, judge_request : JudgeRequest):
        logger.info(f"VMSS #{self.id}: Not enough capacity, adding new VM")

        await self.add_capacity()
        vm = await self.check_available_vm(judge_request.cpus, judge_request.memory)

        if vm is None:
            raise Exception("No vm available for judge request, even after adding capacity")
    
        await self.submit_request_to_vm(judge_request, vm)

    async def submit_request_to_vm(self, judge_request : JudgeRequest, vm : JudgeVM):
        logger.info(f"VMSS #{self.id}: Submitting Request #{judge_request.id} to VM")
        await vm.submit(judge_request)
        
        with judge_request.fulfilled:
            judge_request.fulfilled.wait()

        # Downsize capacity if low usage
        if not vm.is_busy() and os.getenv("NO_DOWN_SIZING", "False") != "True":
            with self.capacity_lock:
                logger.info(f"Deleting VM {vm.vm.name} because it is idle")
                # TODO make sure this doesnt give concurrency issues
                await self.azure.delete_vm(vm.vm.name, vmss_name=self.vmss.name, block=False)
       
            
    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Handle the request for this machine type vmss, an available vm will be found/created and assigned.
        """

        self.submission_queue.put(judge_request)

    async def add_capacity(self):
        """
        Increases capacity of vmss using Azure which could increase the amount of vmss.
        """
        # Increase capacity of vmss with 1 capacity
        logger.info(f"JudgeVMSS #{self.id}: Adding New VM!")
        capacity = self.vmss.sku.capacity
        with self.capacity_lock:
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
                return judgevm
            
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
                
                if self.dormant_vms.empty():
                    # Create a new usable VM
                    judgevm = JudgeVM(vm, machine_name, self.azure, cpus, memory, False)
                else:
                    #Give the first dormant VM the connection
                    judgevm = self.dormant_vms.get()
                    judgevm.vm = vm
                    judgevm.machine_name = machine_name
                    judgevm.free_cpu = cpus
                    judgevm.free_memory = memory
                    with judgevm.dormant_condition:
                        judgevm.dormant_condition.notifyAll()
                
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
