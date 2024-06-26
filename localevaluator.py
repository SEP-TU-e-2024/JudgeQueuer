from custom_logger import main_logger
from evaluators import SubmissionEvaluator
from models import JudgeRequest, JudgeResult
from protocol.judge.commands import StartCommand
from protocol.judge_protocol_handler import protocol_dict, protocol_dict_lock

# Initialize the logger
logger = main_logger.getChild("localevaluator")

class LocalEvaluator(SubmissionEvaluator):
    def __init__(self):
        super().__init__()

    async def submit(self, judge_request: JudgeRequest) -> JudgeResult:
        """
        Submits a judge request to the local judge runner.
        """
        logger.info(f"Submitting judge request {judge_request}")

        # Get the first available judge runner protocol
        with protocol_dict_lock:
            protocol = list(protocol_dict.values())[0]

        command = StartCommand()
        protocol.send_command(command, True,
                              evaluation_settings=judge_request.evaluation_settings,
                              benchmark_instances=judge_request.benchmark_instances,
                              submission_url=judge_request.submission.source_url,
                              validator_url=judge_request.submission.validator_url)

        if command.success:
            result = command.result

            return JudgeResult.success(result)
        else:
            cause = command.cause

            return JudgeResult.error(cause)
