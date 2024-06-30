import asyncio
import os
import queue
import threading

from azure.mgmt.compute.models import (
    VirtualMachineScaleSetVM,
)

from azurewrap import Azure
from custom_logger import main_logger
from models import JudgeRequest, JudgeResult
from protocol.judge.commands import CheckCommand, StartCommand
from protocol.judge_protocol_handler import (
    get_protocol_from_machine_name,
)

# Initialize the logger
logger = main_logger.getChild("JudgeVM")

# Load Azure constants from env vars
NSG_NAME = os.getenv("AZURE_NSG_NAME")
VNET_NAME = os.getenv("AZURE_VNET_NAME")
VNET_SUBNET_NAME = os.getenv("AZURE_VNET_SUBNET_NAME")
VMAPP_RESOURCE_GROUP = os.getenv("AZURE_VMAPP_RESOURCE_GROUP")
VMAPP_GALLERY = os.getenv("AZURE_VMAPP_GALLERY")
VMAPP_NAME = os.getenv("AZURE_VMAPP_NAME")
VMAPP_VERSION = os.getenv("AZURE_VMAPP_VERSION")

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
    capacity_lock: threading.Lock
    dormant_condition: threading.Condition
    submission_queue: queue.Queue[JudgeRequest]
    id: int

    idle_lock: threading.Lock
    max_idle: int
    idle_amount: int

    def __init__(self, vm: VirtualMachineScaleSetVM, machine_name: str, azure: Azure, cpus: int, memory: int, dormant: bool):
        #Reference to the remote VM object
        self.vm = vm
        #Machine name
        self.machine_name = machine_name
        #Reference to the Azure object
        self.azure = azure
        #Amount of free CPU's
        self.free_cpu = cpus
        #Amount of free memory
        self.free_memory = memory
        #Lock for synchronizing capacity changes
        self.capacity_lock = threading.Lock()
        #Condition for checking whether this machine is dormant or not
        self.dormant_condition = threading.Condition()
        #A (threadsafe) queue to store submissions
        self.submission_queue = queue.Queue()
        #Boolean that determines whether this machine should be initialized as dormant
        self.dormant = dormant
        #Lock for changing amount of tasks in idle queue
        self.idle_lock = threading.Lock()
        #Maximum amount of idle tasks
        self.max_idle = 3
        #Current amount of idle tasks
        self.idle_amount = 0

        #Start the request handler
        threading.Thread(target=asyncio.run, args=[self.request_handler()],daemon=True).start()

    async def request_handler(self):
        """
        Worker thread for the JudgeVM. Submits requests from the queue to an actual remote VM
        """
        #Check whether this VM was initialized as dormant
        if self.dormant:
            #If so, acquire the dormant condition lock
            with self.dormant_condition:
                #Unacquire lock and wait for dormant condition to be notified
                self.dormant_condition.wait()
        
        while True:
            #Get the next request in the queue
            judge_request = self.submission_queue.get(block=True)

            #Check whether there is enough space for the next request
            while not await self.check_capacity(judge_request.cpus, judge_request.memory):
                #If not, sleep for one second
                await asyncio.sleep(1)

            #Acquire the idle lock
            with self.idle_lock:
                #Decrease the amount of tasks that were in idle
                self.idle_amount -= 1
            #Acquire the capacity lock
            with self.capacity_lock:
                #Claim the resources for the judge request
                self.free_cpu -= judge_request.cpus
                self.free_memory -= judge_request.memory
            #Submit the request to the vm
            threading.Thread(target=asyncio.run, args=[self.submit_to_vm(judge_request)], daemon=True).start()
                    
    def check_idle_queue(self):
        """
        Returns `True` when the idle queue is not full for this `JudgeVM`
        """
        #Acquire the idle lock
        with self.idle_lock:
            #Check whether the queue is full
            if self.idle_amount >= self.max_idle:
                return False
            else:
                return True
            
    async def check_capacity(self, cpus: int, memory: int) -> bool:
        """
        Check whether this vm has enough capacity to take on the resource allocation
        """
        # Check cpu, gpu and memory capacity of vm and return true if there is enough capacity
        with self.capacity_lock:
            if self.free_cpu >= cpus and self.free_memory >= memory:
                return True

        return False

    async def submit(self, judge_request : JudgeRequest):
        """
        Put a `JudgeRequest` in the submission queue for this VM
        """
        #Acquire the idle lock
        with self.idle_lock:
            #Add one more task to the idle queue
            self.idle_amount += 1
        #Add task to queue
        self.submission_queue.put(judge_request)

    async def submit_to_vm(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Submit a `JudgeRequest` directly to the remote VM related to this JudgeVM object.
        """
        # TODO: communicate the judge request to the VM and monitor status
        logger.info(f"Submitting judge request {judge_request} to VM {self.vm.name} / {self.machine_name}")

        #Get a reference to the protocol
        protocol = get_protocol_from_machine_name(self.machine_name)

        #Create a new start commmand
        command = StartCommand()
        #Submit the request to the remote VM
        protocol.send_command(command, True,
                                evaluation_settings=judge_request.evaluation_settings,
                                benchmark_instances=judge_request.benchmark_instances,
                                submission_url=judge_request.submission.source_url,
                                validator_url=judge_request.submission.validator_url)

        #Acquire the fulfilled condition lock
        with judge_request.fulfilled:
            #Check whether the command was successful
            if command.success:
                #Get the result from the commmand
                result = command.result
                #Set the result in the JudgeRequest reference
                judge_request.result = JudgeResult.success(result)
            else:
                #Get the result from the commmand
                cause = command.cause
                #Set the result in the JudgeRequest reference
                judge_request.result = JudgeResult.error(cause)

            #Notify those waiting for the fulfilled condition
            judge_request.fulfilled.notifyAll()
            #Acquire the capacity lock
            with self.capacity_lock:
                #Free up the resources the JudgeRequest was occupying
                self.free_cpu += judge_request.cpus
                self.free_memory += judge_request.memory


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
