from protocol.judge.commands.start_command import StartCommand


class MockStartCommand(StartCommand):
    success: bool

    def __init__(self):
        pass

    def response(self, response):
        if self.success:
            self.result = "test result"
        else:
            self.cause = "test error"
