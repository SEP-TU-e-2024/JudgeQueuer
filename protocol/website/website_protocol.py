"""
This module containes the WebsiteProtocol class.
"""

from custom_logger import main_logger
from protocol import Connection, Protocol

from .commands import Commands
from .commands.command import Command

logger = main_logger.getChild("website")


class WebsiteProtocol(Protocol):
    """
    The protocol class used by the website.
    """

    connection: Connection

    def __init__(self, connection: Connection):
        self.connection = connection

    def receive_command(self) -> tuple[Command, dict]:
        """
        Handles the incoming commands from the website.
        """

        message = Protocol.receive(self.connection)

        command_id = message["id"]
        command_name = message["command"]
        command_args = message["args"]

        logger.info(f"Received command: {command_name} with args: {command_args}")

        return command_id, command_name, command_args

    async def handle_command(self, command_id: str, command_name: str, args: dict):
        """
        Handles the incoming commands from the website.
        """

        try:
            if command_name not in Commands.__members__:
                logger.error(f"Received unknown command: {command_name}")
                return

            command = Commands[command_name].value
            response = await command.execute(args)
            message = {"id": command_id, "response": response}
            Protocol.send(self.connection, message)

            logger.info(f"Sent response: {response}")

        except Exception as e:
            if e is ConnectionResetError or e is ConnectionAbortedError:
                raise e

            logger.error(
                f"An unexpected error has occured while trying to execute command {command_name}!",
                exc_info=1,
            )
