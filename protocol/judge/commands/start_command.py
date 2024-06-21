"""
This module contains the StartCommand class.
"""

from .command import Command


class StartCommand(Command):
    """
    The StartCommand class is used to start a container on the runner.
    """
    success: bool = True
    result: dict = None
    cause: str = None

    def __init__(self):
        super().__init__(name="START")

    def response(self, response: dict):
        self.success = response["status"] == "ok"

        if self.success:
            self.result = response["results"]
        else:
            self.cause = response["cause"]
