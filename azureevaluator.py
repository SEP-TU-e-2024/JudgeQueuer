from azure.mgmt.compute.models import VirtualMachineScaleSetVM

from azurewrap.base import Azure
from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult, MachineType, ResourceSpecification


class AzureEvaluator(SubmissionEvaluator):
	"""
	An evaluator using Azure Virtual Machine Scale Set.
	"""
	def __init__(self, azure: Azure):
		self.azurevmss_dict = {}
		self.azure = azure

	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# Get the right VMSS, or make one if needed.
		machine_type = judge_request.resource_allocation.machine_type
		if machine_type in self.azurevmss_dict:
			azurevmss = self.azurevmss_dict[machine_type]
		else:
			azurevmss_name = "my-vmssnu_" + machine_type.descriptor
			vmss = await self.azure.create_vmss(azurevmss_name)
			azurevmss = AzureVMSS(machine_type, azurevmss_name, vmss, self.azure)
			self.azurevmss_dict[machine_type] = azurevmss

		# Then forward call to that.
		judge_result = await azurevmss.submit(judge_request)

		if azurevmss.is_empty():
			# azurevmss is empty with no vms, close azurevmss
			azurevmss.close()
			self.azurevmss_dict.pop(machine_type)

		return judge_result

class AzureVMSS:
	"""
	An Azure Virtual Machine Scale Set. A Set contains a single machine type.
	"""
	def __init__(self, machine_type: MachineType, azurevmss_name: str, vmss, azure: Azure):
		self.machine_type: machine_type
		self.azurevmss_name: azurevmss_name
		self.azurevm_dict = {}
		self.vmss = vmss
		self.azure = azure

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
		judge_result = await self.submit_vm(vm, judge_request)

		# Reduce capacity and update vm dict
		self.reduce_capacity()
		self.update_vm_dict()

		return judge_result

	async def add_capacity(self):
		# Increase capacity of vmss with an arbitrary max of 5
		capacity = self.vmss.sku.capacity
		if capacity < 5:
			await self.azure.set_capacity(capacity + 1, self.azurevmss_name)
		
		# Update vm_dict, vm(s) could have been added
		self.update_vm_dict()
			
	async def reduce_capacity(self):
		# Decrease capacity of vmss
		capacity = self.vmss.sku.capacity

		# There needs to be capacity to be removed
		if capacity > 0:
			await self.azure.set_capacity(capacity - 1, self.azurevmss_name)

		# Update vm_dict, vm(s) could have been deleted
		self.update_vm_dict()
	
	async def submit_vm(self, vm: VirtualMachineScaleSetVM, judge_request: JudgeRequest) -> JudgeResult:
		azurevm = self.vm_dict[vm.name]
		judge_result = await azurevm.submit(self, judge_request)

		return judge_result
	
	async def check_available_vm(self, resource_allocation: ResourceSpecification) -> VirtualMachineScaleSetVM:
		# Get the list of vms
		vms = self.azure.list_vms(self.machine_type, self.azurevmss_name)

		# Update vm_dict, make sure the dict is up to date
		self.update_vm_dict()

		# Go over the virtual machine to find one with enough capacity
		for vm in vms:
			# Get the azure vm class instance associated to the vm
			if self.vm_dict[vm.name]:
				azurevm = self.vm_dict[vm.name]
			
			# Check if there is enough free resource capacity on this vm
			if azurevm.capacity(resource_allocation):
				
				return vm
		
		# No vm found
		return None
	
	async def update_vm_dict(self):
		vms = self.azure.list_vms(self.machine_type, self.azurevmss_name)

		for vm in vms:
			# Check if each vm has a AzureVM class stored to it in dict
			if not self.vm_dict[vm.name]:
				# Create and safe vm class
				azurevm = AzureVM(vm, self.azure)
				self.vm_dict[vm.name] = azurevm

		for key in self.vm_dict:
			azurevm = self.vm_dict[key]
			# Check if the vms in the dictionary are still alive
			if not azurevm.alive():
				# Remove azurevm from dictionary
				self.vm_dict.pop(key)

	async def is_empty(self) -> bool:
		"""
		Check if there are no vms part of this vmss
		"""
		self.update_vm_dict()
		if self.azurevm_dict:
			# Not empty
			return False
		return True

	async def close(self):
		"""
		Close the vmss and check if no associated vms
		"""
		self.azure.delete_vmss(self.machine_type)
		if self.azurevm_dict:
			raise Exception("AzureVMSS was tried to be closed while having associated vms")

class AzureVM:
	"""
	An Azure Virtual Machine.
	"""
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
