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
logger = main_logger.getChild("azureevaluator")

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
        self.vm = vm
        self.machine_name = machine_name
        self.azure = azure
        self.free_cpu = cpus
        self.free_memory = memory
        self.capacity_lock = threading.Lock()
        self.dormant_condition = threading.Condition()
        self.submission_queue = queue.Queue()
        self.id = 0
        self.dormant = dormant

        self.idle_lock = threading.Lock()
        self.max_idle = 3
        self.idle_amount = 0

        threading.Thread(target=asyncio.run, args=[self.request_handler()],daemon=True).start()

    async def request_handler(self):
        if self.dormant:
            with self.dormant_condition:
                logger.info(f"VM #{self.id}: Going dormant, no connection yet")
                #We need to wait untill VM has been initialized
                self.dormant_condition.wait()

        logger.info(f'VM #{self.id}: Request handling thread succesfully started')
        
        while True:
            #Check whether the queue is empty
            if self.submission_queue.empty():
                await asyncio.sleep(1)
                continue
            else:
                #There is a new request to handle
                request = self.submission_queue.get()
                assert type(request) == JudgeRequest

                while not self.check_capacity(request.cpus, request.memory):
                    await asyncio.sleep(1)
                logger.info(f"VM #{self.id} handling new request: #{request.id}")
                threading.Thread(target=asyncio.run, args=[self.submit_to_vm(request)], daemon=True).start()
                    

    def check_idle_queue(self):
        with self.idle_lock:
            if self.idle_amount == self.max_idle:
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
        self.submission_queue.put(judge_request)
        with self.capacity_lock:
            self.free_cpu -= judge_request.cpus
            self.free_memory -= judge_request.memory

    async def submit_to_vm(self, judge_request: JudgeRequest) -> JudgeResult:
        # TODO: communicate the judge request to the VM and monitor status
        logger.info(f"Submitting judge request {judge_request} to VM {self.vm.name} / {self.machine_name}")

        protocol = get_protocol_from_machine_name(self.machine_name)

        command = StartCommand()
        protocol.send_command(command, True,
                                evaluation_settings=judge_request.evaluation_settings,
                                benchmark_instances=judge_request.benchmark_instances,
                                submission_url=judge_request.submission.source_url,
                                validator_url=judge_request.submission.validator_url)

        with judge_request.fulfilled:
            if command.success:
                result = command.result

                judge_request.result = JudgeResult.success(result)
            else:
                cause = command.cause

                judge_request.result = JudgeResult.error(cause)
            judge_request.fulfilled.notifyAll()
            with self.capacity_lock:
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
