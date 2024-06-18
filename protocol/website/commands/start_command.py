import azureevaluator
from custom_logger import main_logger
from models import (
    JudgeRequest,
    MachineType,
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
        evaluation_settings: dict = args["evaluation_settings"]
        benchmark_instances: dict[str, str] = args["benchmark_instances"] # dict of ID to URL
        submission_url: str = args["submission_url"]
        validator_url: str = args["validator_url"]

        # Extract relevant part of the evaluation settings
        machine_type = MachineType.from_name(evaluation_settings["machine_type"])
        cpus = evaluation_settings["cpu"]
        memory = evaluation_settings["memory"]

        # Form models for the judge request
        submission_type = SubmissionType.CODE
        submission = Submission(submission_type, submission_url, validator_url)
        judge_request = JudgeRequest(submission, machine_type, cpus, memory, evaluation_settings, benchmark_instances)

        # Submit the request to the evaluator
        try:
            judge_result = await azureevaluator.get_instance().submit(judge_request)

            return {"status": "ok", "result": judge_result.result}
        except Exception:
            logger.error("An unexpected error has occured while trying to submit a judge request to the evaluator", exc_info=1)

            return {"status": "error"}
