from azure.mgmt.compute.models import (
    VirtualMachineScaleSetVM,
)


class MockVM(VirtualMachineScaleSetVM):
    def __init__(self):
        self.name = "test_vm"
        pass
