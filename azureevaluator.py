import os

from azure.mgmt.compute.models import VirtualMachineScaleSetVM
from dotenv import load_dotenv

from azurewrap.base import Azure
from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult, MachineType, ResourceSpecification

# Initialize environment variables from the `.env` file
load_dotenv()

# Load Azure constants from env vars
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = os.getenv("AZURE_RESOURCE_GROUP_NAME")

azure = Azure(subscription_id=SUBSCRIPTION_ID, resource_group_name=RESOURCE_GROUP_NAME)

class AzureEvaluator(SubmissionEvaluator):
	"""
	An evaluator using Azure Virtual Machine Scale Set.
	"""
	def __init__(self):
		self.vmss_dict = {}

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# get the right VMSS, or make one if needed.
		machine_type = judge_request.resource_allocation.machine_type
		if machine_type in self.vmss_dict.keys():
			avmss = self.vmss_dict[machine_type]
		else:
			avmss_name = "my-vmssnu_" + machine_type.descriptor
			vmss = await azure.create_vmss(avmss_name)
			avmss = AzureVMSS(machine_type, avmss_name, vmss)
			self.vmss_dict[machine_type] = avmss

		# Then forward call to that.
		judge_result = await avmss.submit(judge_request)

		return judge_result

class AzureVMSS:
	"""
	An Azure Virtual Machine Scale Set. A Set contains a single machine type.
	"""
	def __init__(self, machine_type: MachineType, avmss_name: str, vmss):
		self.machine_type: machine_type
		self.avmss_name: avmss_name
		self.avm_dict = {}
		self.vmss = vmss

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		resource_allocation = judge_request.resource_allocation

		# Get a right vm that is available
		vm = self.check_available_vm(resource_allocation)

		# If no available vm than add capacity
		if vm is None:
			# Get available vm after the added capacity, error if no available
			self.add_capacity()

			vm = self.check_available_vm(resource_allocation)

			if vm is None:
				# Throw exception
				raise Exception("No vm available for judge request, even after adding capacity")

		# Submit using the vm the judge request
		return await self.submit_vm(vm, judge_request)


	async def add_capacity(self):
		# Increase capacity of vmss with an arbitrary max of 5
		capacity = self.vmss.sku.capacity
		if (capacity < 5):
			await azure.set_capacity(capacity + 1, self.avmss_name)
		
			
	async def reduce_capacity(self):
		# Decrease capacity of vmss, always keep at least capacity 1
		capacity = self.vmss.sku.capacity
		if (capacity > 1):
			await azure.set_capacity(capacity - 1, self.avmss_name)

		return vm
			
	
	async def submit_vm(self, vm: VirtualMachineScaleSetVM, judge_request: JudgeRequest) -> JudgeResult:
		avm = AzureVM(vm)
		# self.vm_dict[vm.name] = avm
		judge_result = await avm.submit(self, judge_request)

		return judge_result
	
	async def check_available_vm(self, resource_allocation: ResourceSpecification):
		# Get the list of vms
		vms = azure.list_vms(self.machine_type, self.avmss_name)
		
		for vm in vms:
			# Get the azure vm class instance associated to the vm
			if (self.vm_dict[vm.name]):
				avm = self.vm_dict[vm.name]
			
			# Check if there is enough free resource capacity on this vm
			if (avm.capacity(resource_allocation)):
				
				return vm
		
		# no vm found
		return None
			
	async def close(self):
		azure.delete_vmss(self.machine_type)

class AzureVM:
	"""
	An Azure Virtual Machine.
	"""
	def __init__(self, vm):
		self.vm = vm
	async def capacity(self, resource_allocation: ResourceSpecification):
		pass

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# TODO: communicate the judge request to the VM and monitor status
		pass
