
class MockOSProfile:
    def __init__(self):
        pass

    computer_name = "test_computer_name"

class MockVM():
    def __init__(self, name='test_vm'):
        self.name = name
        self.os_profile = MockOSProfile()

