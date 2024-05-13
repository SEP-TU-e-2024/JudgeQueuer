from enum import Enum


class MachineType:
	"""
	A type of machine.
	"""
	# TODO: improve description
	descriptor: str

class ResourceSpecification:
	"""
	The specification of allocated resources to evaluate a submission.
	"""
	num_cpus: int
	num_memory: int # in MB
	num_gpu: int
	machine_type: 'MachineType'

class SubmissionType(Enum):
	"""
	The type of a submission: either code, or solution.
	"""
	CODE = 1
	SOLUTION = 2

class Submission:
	"""
	A submission that should be evaluated.
	"""
	type: 'SubmissionType'
	source_url: str

class JudgeRequest:
	"""
	A request for a submission to be evaluated according to some resource specification.
	"""
	submission: 'Submission'
	resource_allocation: 'ResourceSpecification'

class JudgeResult:
	"""
	The result of evaluation by a judge.

	Formatted in JSON.
	"""
	result: str
