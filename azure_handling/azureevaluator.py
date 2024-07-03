import asyncio
import os
import queue
import threading

from azurewrap import Azure
from custom_logger import main_logger
from evaluators import SubmissionEvaluator
from models import JudgeRequest, MachineType

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
    
    def __init__(self, azure: Azure):
        """
        Constructor of the AzureEvaluator
        """
        #Call the constructor of the inherited class
        super().__init__()
        #Initialize a dictionary to map remote vm's to local vm classes
        self.judgevmss_dict = {}
        #Initialize object to reference Azure
        self.azure = azure
        #Create a (threadsafe) queue object to keep track of submissions
        self.submission_queue = queue.Queue()

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
        
        #Start worker thread, which handles all the incoming requests
        threading.Thread(target=asyncio.run, args=[self.handle_requests()], daemon=True).start()


    async def handle_requests(self):
        """
        Checks for incoming requests and submits them to active VMSS's.

        If no VMSS available creates a new one.
        """
        while True:
            #Blocks until a new request is available
            judge_request = self.submission_queue.get(block=True)
            #Check whether the request can be handled by any of the current VMSS's
            if judge_request.machine_type in self.judgevmss_dict:
                #If so, assign this VMSS
                judgevmss = self.judgevmss_dict[judge_request.machine_type]
            else:
                #If not, create a new one
                judgevmss = await self.create_vmss(judge_request.machine_type)
            #Submit the request in a new thread
            threading.Thread(target=asyncio.run, args=[self.forward_request(judgevmss, judge_request)], daemon=True).start()

    async def forward_request(self, judge_vmss, judge_request : JudgeRequest):
        """
        Forwards a given request to a given VMSS.
        """
        await judge_vmss.submit(judge_request)

    async def create_vmss(self, machine_type: MachineType) -> JudgeVMSS:
        """
        Creates a new VMSS appropriate for the given machine type.
        """
        # Get the right VMSS, or make one if needed
        judgevmss_name = "benchlab_judge_" + machine_type.name

        logger.info(f"Creating VMSS {judgevmss_name}")

        await self.azure.create_vmss(
            judgevmss_name,
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
        """
        Submit a new judge request to this AzureEvaluator
        """
        #Add the request to the submission queue, for it to be dealt with by the worker thread
        self.submission_queue.put(judge_request)

        #Acquire condition lock (preventing deadlocks)
        with judge_request.fulfilled:
            #Unacquire lock and wait until the judge_request has been fulfilled
            judge_request.fulfilled.wait()
        #Return the result of the judge_request through the callback
        return judge_request.result

