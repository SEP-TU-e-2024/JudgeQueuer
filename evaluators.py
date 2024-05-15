from abc import ABC

from models import JudgeRequest, JudgeResult


class SubmissionEvaluator(ABC):
	"""
	An object capable of performing judge requests by evaluating submissions.
	"""
	async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
		"""
		Submits a judge request to be evaluated.
		"""
		raise NotImplementedError()
