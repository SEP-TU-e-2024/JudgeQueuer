"""
This module contains the StartCommand class.
"""

from .command import Command


class StartCommand(Command):
    """
    The StartCommand class is used to start a container on the runner.
    """

    def __init__(self):
        super().__init__(name="START")

    def response(self, response: dict):
        print("Got VM response:", response)
        self.result = response["result"]
