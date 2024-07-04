from protocol.judge.commands.command import Command
from protocol.judge.judge_protocol import JudgeProtocol


class MockJudgeProtocol(JudgeProtocol):

    def __init__(self):
        pass

    def send_command(self, command: Command, block: bool = False, timeout: float = None, **kwargs):
        return command.response(None)