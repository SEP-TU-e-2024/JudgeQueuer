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
logger = main_logger.getChild("JudgeVMSS")

# Maximum idling time for a VM, before it is deleted


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
    judge_dict_lock: threading.Lock
    submission_queue: queue.Queue[JudgeRequest]
    dormant_vms: queue.Queue[JudgeVM]

    def __init__(self, machine_type: MachineType, judgevmss_name: str, vmss: VirtualMachineScaleSet , azure: Azure):
        """
        Constructor of the JudgeVMSS class.
        """
        #Store the type of machine for this VMSS
        self.machine_type = machine_type
        #Store the name of this VMSS
        self.judgevmss_name = judgevmss_name
        #Store a dictionary to keep map remote VM's to local JudgeVM objects
        self.judgevm_dict = {}
        #Store a reference to the Azure VMSS object
        self.vmss = vmss
        #Store a reference to the Azure object
        self.azure = azure
        #Create a lock for changing the capacity of this VMSS
        self.capacity_lock = threading.Lock()
        #Create a lock for changing the JudgeVM dictionary
        self.judge_dict_lock = threading.Lock()
        #Create a queue object to keep track of submissions for this VMSS
        self.submission_queue = queue.Queue()
        #Create a queue to keep track of which local VM objects still need a remote connection
        self.dormant_vms = queue.Queue()

        #Start the main worker thread
        threading.Thread(target=asyncio.run, args=[self.request_handler()], daemon=True).start()

    async def request_handler(self):
        """
        Main worker thread, finds new requests and dishes them out to individual VM's.
        Creates new VM's if needed.
        """
        #Add already existing VM's to the VM dict
        await self.__update_vm_dict()
        while True:
            #Get the next request in the queue
            request = self.submission_queue.get(block=True)
            #Boolean to track whether the request has been assigned or not
            assigned = False
            #Loop over all vm names in the judgevm dictionary
            for vm_name in self.judgevm_dict:
                logger.info('Assigned to live VM')
                #Get the corresponding JudgeVM object
                with self.judge_dict_lock:
                    judgevm = self.judgevm_dict[vm_name]

                #Check whether there is enough capacity, or there is still space in the idle queue
                if await judgevm.check_capacity(request.cpus, request.memory) or judgevm.check_idle_queue():
                    #Assign the request to this VM
                    threading.Thread(target=asyncio.run, args=[self.forward_request(request, judgevm)], daemon=True).start()
                    #Mark the request as assigned
                    assigned = True
                    break
            
            #If we the request has been assigned, move onto the next request
            if assigned:
                continue

            #Loop over all the dormant VM's
            for judgevm in self.dormant_vms.queue:
                #Check whether there is enough capacity, or there is still space in the idle queue
                if judgevm.check_idle_queue():
                    logger.info('Assigned to dormant VM')
                    #Assign it to a dormant vm
                    threading.Thread(target=asyncio.run, args=[self.forward_request(request, judgevm)], daemon=True).start()
                    #Mark the request as assigned
                    assigned = True
                    break

            #Check if the requst has been assigned so far
            if not assigned:
                logger.info('Create new VM')
                #We need to create a new VM (dormant)
                judgevm = JudgeVM(None, None, self.azure, request.cpus, request.memory, True)
                #Add it to the queue of dormant vm's
                self.dormant_vms.put(judgevm)

                #Submit the request to this VM (it will be executed as soons at the remote has more capacity)
                threading.Thread(target=asyncio.run, args=[self.forward_request(request,judgevm)], daemon=True).start()
                #Add more capacity in Azure
                threading.Thread(target=asyncio.run, args=[self.add_capacity()],daemon=True).start()

    async def forward_request(self, judge_request : JudgeRequest, vm : JudgeVM):
        """
        Given a Judge Request and Virtual Machine, forward the request to the machine.
        """
        #Submit the request to the given VM
        await vm.submit(judge_request)
        #Acquire the lock for the fullfiment condition
        with judge_request.fulfilled:
            #Release lock and wait untill the judge request has been fulfilled
            judge_request.fulfilled.wait()

        # Downsize capacity if low usage
        if not vm.is_busy() and os.getenv("NO_DOWN_SIZING", "False") != "True":
            #Call the removal function
            await self.start_vm_removal_time(vm)
    
    async def start_vm_removal_time(self, judge_vm : JudgeVM):
        """
        Removes a specified VM if they are idle for MAX_VM_IDLE_TIME.
        If MAX_VM_IDLE_TIME = 0, instantly remove it.
        """
        MAX_VM_IDLE_TIME = int(os.getenv("MAX_VM_IDLE_TIME", 60))
        
        for i in range(MAX_VM_IDLE_TIME):
            #Check if the VM is busy
            if judge_vm.is_busy():
                #If so, we don't need to delete
                return
            else:
                #Sleep for one second
                await asyncio.sleep(1)
        #Acquire the capacity lock
        with self.capacity_lock:
            logger.info(f"Deleting VM {judge_vm.vm.name} because it is idle")
            #Remove the vm
            with self.judge_dict_lock:
                if judge_vm.vm.name in self.judgevm_dict.keys():
                    self.judgevm_dict.pop(judge_vm.vm.name)
            await self.azure.delete_vm(judge_vm.vm.name, vmss_name=self.vmss.name, block=False)

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
        logger.info(f"JudgeVMSS #{self.vmss.name}: Adding New VM!")
        vmss = await self.azure.get_vmss(self.vmss.name)
        capacity = vmss.sku.capacity
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
        with self.judge_dict_lock:
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

        with self.judge_dict_lock:
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
                    # Adjust for the CPU and memory overhead for the OS and runner code overhead
                    cpus -= int(os.getenv("MIN_CPUS", 1))
                    memory -= int(os.getenv("MIN_MEMORY", 512))
                    if cpus <= 0:
                        raise Exception("VM does not have enough cpus")
                    if memory <= 0:
                        raise Exception("VM does not have enough memory")

                    #Check if there is a dormant vm waiting for a connection
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
                        #Tell the dormant vm to wake up and start taking requests
                        with judgevm.dormant_condition:
                            judgevm.dormant_condition.notifyAll()
                    #Add the dormant vm to the judge dict
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
