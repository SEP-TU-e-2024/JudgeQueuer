from enum import Enum


class MachineType:
	"""
	A type of machine.
	"""
	# TODO: improve description
	
	def __init__(self, descriptor: str):
		self.descriptor = descriptor

class ResourceSpecification:
	"""
	The specification of allocated resources to evaluate a submission.
	"""

	def __init__(self, num_cpu: int, num_memory: int, num_gpu: int, machine_type: 'MachineType'):
		self.num_cpu = num_cpu
		self.num_memory = num_memory # in MB
		self.num_gpu = num_gpu
		self.machine_type = machine_type

class SubmissionType(Enum):
	"""
	The type of a submission: either code, or solution.
	"""
	CODE = 1
	SOLUTION = 2
	
	def __init__(self, type: Enum):
		self.type = type


class Submission:
	"""
	A submission that should be evaluated.
	"""

	def __init__(self, type: 'SubmissionType', source_url: str):
		self.type = type
		self.source_url = source_url

class JudgeRequest:
	"""
	A request for a submission to be evaluated according to some resource specification.
	"""

	def __init__(self, submission: 'Submission', resource_allocation: 'ResourceSpecification'):
		self.submission = submission
		self.resource_allocation = resource_allocation

class JudgeResult:
	"""
	The result of evaluation by a judge.

	Formatted in JSON.
	"""

	def __init__(self, result: str):
		self.result = result
