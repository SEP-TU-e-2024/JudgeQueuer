from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult


class AzureEvaluator(SubmissionEvaluator):
	"""
	An evaluator using Azure Virtual Machine Scale Set.
	"""
	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# TODO: get the right VMSS, or make one if needed. Then forward call to that.
		pass

class AzureVMSS:
	"""
	An Azure Virtual Machine Scale Set.
	"""
	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# TODO: get the right VM, or scale up if not available.
		pass

class AzureVM:
	"""
	An Azure Virtual Machine.
	"""
	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		# TODO: communicate the judge request to the VM and monitor status
		pass
