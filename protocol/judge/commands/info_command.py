"""
This module contains the InfoCommand class.
"""

from .command import Command


class InfoCommand(Command):
    """
    The InfoCommand class is used to request machine and VM information from a runner.
    """

    def __init__(self):
        super().__init__(name="INFO")

    def response(self, response: dict):
        self.machine_name = response["machine_name"]
