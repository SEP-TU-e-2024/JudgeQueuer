from abc import ABC

from models import JudgeRequest, JudgeResult

instance = None
"""
Keep track of the instance of the AzureEvaluator class, for access in Command classes.
"""
def get_instance() -> 'SubmissionEvaluator':
    """
    Get the instance of the AzureEvaluator class.
    """
    if instance is None:
        raise Exception("AzureEvaluator instance is not initialized")

    return instance


class SubmissionEvaluator(ABC):
    def __init__(self):
        # Update the global instance variable with this instance
        global instance
        instance = self

    """
    An object capable of performing judge requests by evaluating submissions.
    """
    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Submits a judge request to be evaluated.
        """
        raise NotImplementedError()

    async def initialize(self):
        """
        Initialize the evaluator.
        """
        #Create a (threadsafe) queue object to keep track of submissions
        pass
