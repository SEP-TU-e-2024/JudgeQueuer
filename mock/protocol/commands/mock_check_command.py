from protocol.judge.commands.check_command import CheckCommand


class MockCheckCommand(CheckCommand):
    success: bool

    def __init__(self):
        pass

    def response(self, response):
        if self.success:
            return
        else:
            raise Exception("Test Error")
