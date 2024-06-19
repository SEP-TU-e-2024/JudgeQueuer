"""
This module contains the CheckCommand class.
"""

from .command import Command


class CheckCommand(Command):
    """
    The CheckCommand class is used to check the status of the runner.
    """

    def __init__(self):
        super().__init__(name="CHECK")

    def response(self, response: dict):
        if response["status"] != "ok":
            raise Exception("Runner is healthy")
