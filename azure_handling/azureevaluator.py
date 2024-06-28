import asyncio
import os
import queue
import threading
import time

from azurewrap import Azure
from custom_logger import main_logger
from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult, MachineType

from .judgevmss import JudgeVMSS

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

class AzureEvaluator(SubmissionEvaluator):
    """
    An evaluator using Azure Virtual Machine Scale Set.
    """
    judgevmss_dict: dict['MachineType', 'JudgeVMSS']
    azure: Azure
    submission_queue : queue.Queue[JudgeRequest]
    lock : threading.Lock
    
    def __init__(self, azure: Azure):
        super().__init__()
        self.judgevmss_dict = {}
        self.azure = azure
        self.submission_queue = queue.Queue()
        self.assigned_requests = {}
        self.lock = threading.Lock()

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
        
        logger.info('Starting request handling thread')
        threading.Thread(target=asyncio.run, args=[self.handle_requests()], daemon=True).start()


    async def handle_requests(self):
        logger.info('Request handling thread succesfully started')
        while True:
            #Check whether the queue is empty
            if self.submission_queue.empty():
                #If so, sleep for one second so we don't overload
                time.sleep(1)
                continue
            else:
                #There is a new request to handle
                request = self.submission_queue.get()
                assert type(request) == JudgeRequest
                request.id = self.get_new_req_id()
                logger.info(f"AzureEvaluator handling new request: #{request.id}")
                
                if request.machine_type in self.judgevmss_dict:
                    judgevmss = self.judgevmss_dict[request.machine_type]
                else:
                    judgevmss = self.create_vmss(request.machine_type, self.get_new_id())
                
                self.assign_request(judgevmss.id, request.id)

                #Handle the submission in a separate thread
                # threading.Thread(target=self.submit_request, args=[judgevmss, request], daemon=True).start()
                await self.submit_request(judgevmss, request)

    def assign_request(self, vmss_id, req_id):
        if vmss_id not in self.assigned_requests.keys():
            self.assigned_requests[vmss_id] = []
        self.assigned_requests[vmss_id] += [req_id]

    def get_new_vmss_id(self):
        if len(self.assigned_requests.keys()) == 0:
            return 1
        else:
            return max(self.assigned_requests.keys()) + 1
    
    def get_new_req_id(self):
        if len(self.assigned_requests.values()) == 0:
            return 1
        else:
            return max(self.assigned_requests.values()) + 1
    
    async def submit_request(self, judge_vmss, judge_request : JudgeRequest):  # noqa: F821
        logger.info(f"Submitting request {judge_request.id} to {judge_vmss.judgevmss_name}")
        r = await judge_vmss.submit(judge_request)
        assert type(r) == JudgeResult
        logger.info(f"Finished Request {judge_request.id} : Result  {r.result}")


    async def create_vmss(self, machine_type: MachineType, id: int) -> JudgeResult:
        """
        Handles finding, creating and deletion of vmss that is appropriate for this judgeRequest.
        """
        logger.info(f"Starting new vmss: {machine_type.name}")


        # Get the right VMSS, or make one if needed
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

        return judgevmss
    
    async def submit(self, judge_request : JudgeRequest):
        self.submission_queue.put(judge_request)
        logger.info(f"Submitting submission #{judge_request.id}")
        #Wait untill submission is fulfilled
        with judge_request.fulfilled:
            logger.info(f"Submission #{judge_request.id} waiting for fulfillment")
            judge_request.fulfilled.wait()
        logger.info(f"Judge result #{judge_request.id} fulfilled")
        return judge_request.result

