import azureevaluator
from custom_logger import main_logger
from models import (
    JudgeRequest,
    MachineType,
    ResourceSpecification,
    Submission,
    SubmissionType,
)

from .command import Command

# Initialize the logger
logger = main_logger.getChild("start_command")


class StartCommand(Command):
    """
    The StartCommand class is used to start a container on the runner.
    """

    @staticmethod
    async def execute(args: dict):
        # Deserialization of the arguments
        machine_type = MachineType.from_name(args["machine_type"])
        submission_type = {"code": SubmissionType.CODE, "solution": SubmissionType.SOLUTION}[args["submission_type"]]
        resource_specification = ResourceSpecification(num_cpu=args["cpus"],
                                                       num_memory=args["memory"],
                                                       num_gpu=args["gpus"],
                                                       machine_type=machine_type,
                                                       time_limit=args["time_limit"])
        submission = Submission(submission_type, args["source_url"], args["validator_url"])
        judge_request = JudgeRequest(submission, resource_specification)

        # Submit the request to the evaluator
        try:
            judge_result = await azureevaluator.get_instance().submit(judge_request)

            return {"status": "ok", "result": judge_result.result}
        except Exception:
            logger.error("An unexpected error has occured while trying to submit a judge request to the evaluator", exc_info=1)

            return {"status": "error"}
