import os
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
    lock : threading.Lock

    def __init__(self, vm: VirtualMachineScaleSetVM, machine_name: str, azure: Azure, cpus: int, memory: int):
        self.vm = vm
        self.machine_name = machine_name
        self.azure = azure
        self.free_cpu = cpus
        self.free_memory = memory
        self.lock = threading.Lock()

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
