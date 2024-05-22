from typing import Dict

from azure.mgmt.compute.models import VirtualMachineScaleSet, VirtualMachineScaleSetVM

from azurewrap.base import Azure
from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult, MachineType, ResourceSpecification


class AzureEvaluator(SubmissionEvaluator):
	"""
	An evaluator using Azure Virtual Machine Scale Set.
	"""
	# TODO: make sure that we have only 1 MachineType instance per its descriptor, otherwise this dict doesn't work
	judgevmss_dict: Dict['MachineType', 'JudgeVMSS']
	azure: Azure
	
	def __init__(self, azure: Azure):
		self.judgevmss_dict = {}
		self.azure = azure

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# Get the right VMSS, or make one if needed.
		machine_type = judge_request.resource_allocation.machine_type
		if machine_type in self.judgevmss_dict:
			judgevmss = self.judgevmss_dict[machine_type]
		else:
			judgevmss_name = "benchlab_judge_" + machine_type.descriptor
			await self.azure.create_vmss(judgevmss_name)
			vmss = await self.azure.get_vmss(judgevmss_name)
			judgevmss = JudgeVMSS(machine_type, judgevmss_name, vmss, self.azure)
			self.judgevmss_dict[machine_type] = judgevmss

		# Then forward call to that.
		judge_result = await judgevmss.submit(judge_request)

		if judgevmss.is_empty():
			# judgevmss is empty with no vms, close judgevmss
			await judgevmss.close()
			self.judgevmss_dict.pop(machine_type)

		return judge_result

class JudgeVMSS:
	"""
	An Azure Virtual Machine Scale Set. A Set contains a single machine type.
	"""
	machine_type: 'MachineType'
	judgevmss_name: str
	judgevm_dict: Dict[str, 'Judgevm']
	vmss: VirtualMachineScaleSet
	azure: Azure
	
	def __init__(self, machine_type: MachineType, judgevmss_name: str, vmss: VirtualMachineScaleSet , azure: Azure):
		self.machine_type = machine_type
		self.judgevmss_name = judgevmss_name
		self.judgevm_dict = {}
		self.vmss = vmss
		self.azure = azure

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		resource_allocation = judge_request.resource_allocation

		# Get a right vm that is available
		vm = await self.check_available_vm(resource_allocation)

		# If no available vm than add capacity
		if vm is None:
			# Get available vm after the added capacity, error if no available
			await self.add_capacity()

			# TODO: if concurrency, this may give issues (between line above and below, other thread may have used new capacity, so it is no longer available)
			vm = await self.check_available_vm(resource_allocation)

			if vm is None:
				# Throw exception
				raise Exception("No vm available for judge request, even after adding capacity")

		# Submit using the vm the judge request
		judge_result = await self.submit_vm(vm, judge_request)

		# Reduce capacity and update vm dict
		await self.reduce_capacity()
		await self.update_vm_dict()

		return judge_result

	async def add_capacity(self):
		# Increase capacity of vmss with an arbitrary max of 5
		capacity = self.vmss.sku.capacity
		if capacity < 5:
			await self.azure.set_capacity(capacity + 1, self.judgevmss_name)
		
		# Update judgevm_dict, vm(s) could have been added
		await self.update_vm_dict()
			
	async def reduce_capacity(self):
		# Decrease capacity of vmss
		capacity = self.vmss.sku.capacity

		# There needs to be capacity to be removed
		if capacity > 0:
			await self.azure.set_capacity(capacity - 1, self.judgevmss_name)

		# Update vm_dict, vm(s) could have been deleted
		await self.update_vm_dict()
	
	async def submit_vm(self, vm: VirtualMachineScaleSetVM, judge_request: JudgeRequest) -> JudgeResult:
		judgevm = self.judgevm_dict[vm.name]
		judge_result = await judgevm.submit(self, judge_request)

		return judge_result
	
	async def check_available_vm(self, resource_allocation: ResourceSpecification) -> VirtualMachineScaleSetVM | None:
		# Get the list of vms
		vms = await self.azure.list_vms(self.judgevmss_name)

		# Update vm_dict, make sure the dict is up to date
		await self.update_vm_dict()

		# Go over the virtual machine to find one with enough capacity
		for vm in vms:
			# Get the azure vm class instance associated to the vm
			if vm.name in self.judgevm_dict:
				judgevm = self.judgevm_dict[vm.name]
			
			# Check if there is enough free resource capacity on this vm
			if await judgevm.capacity(resource_allocation):
				
				return vm
		
		# No vm found
		return None
	
	async def update_vm_dict(self):
		vms = await self.azure.list_vms(self.judgevmss_name)

		for vm in vms:
			# Check if each vm has a judgevm class stored to it in dict
			if vm.name not in self.judgevm_dict:
				# Create and safe vm class
				judgevm = Judgevm(vm, self.azure)
				self.judgevm_dict[vm.name] = judgevm

		for key in list(self.judgevm_dict):
			judgevm = self.judgevm_dict[key]
			# Check if the vms in the dictionary are still alive
			if not await judgevm.alive():
				# Remove judgevm from dictionary
				self.judgevm_dict.pop(key)

	async def is_empty(self) -> bool:
		"""
		Check if there are no vms part of this vmss
		"""
		self.update_vm_dict()
		if bool(self.judgevm_dict):
			# Not empty
			return False
		return True

	async def close(self):
		"""
		Close the vmss and check if no associated vms
		"""
		if bool(self.judgevm_dict):
			raise Exception("judgevmSS was tried to be closed while having associated vms")

		await self.azure.delete_vmss(self.machine_type)

class Judgevm:
	"""
	An Azure Virtual Machine.
	"""
	vm: VirtualMachineScaleSetVM
	azure: Azure
	free_cpu: int
	free_gpu: int
	free_memory: int

	def __init__(self, vm: VirtualMachineScaleSetVM, azure: Azure):
		self.vm = vm
		self.azure = azure
		self.free_cpu = 0
		self.free_gpu = 0
		self.free_memory = 0
	
	async def capacity(self, resource_allocation: ResourceSpecification) -> bool:
		pass
		# TODO implement check for capacity
		# Check cpu, gpu and memory capacity of vm and return true if there is enough capacity
		if self.free_cpu >= resource_allocation.num_cpu and self.free_gpu >= resource_allocation.num_gpu and self.free_memory >= resource_allocation.num_memory:
			return True
		
		return False

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# TODO: communicate the judge request to the VM and monitor status
		# TODO: keep track of free resources
		pass

	async def alive(self):
		# TODO check if self.vm is actually still alive (decreasing capacity in vmss can remove it, or by calling delete_vm)
		pass
