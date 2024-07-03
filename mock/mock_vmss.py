from azure.mgmt.compute.models import (
    VirtualMachineScaleSet,
)

from models import JudgeRequest


class SKU:
    def __init__(self, name, tier):
        self.name = name
        self.tier = tier

class MockVMSS(VirtualMachineScaleSet):
    capacity: int
    name: str
    sku: SKU

    def __init__(self, sku_name, sku_tier):
        self.capacity = 0
        self.name = ""
        self.sku = SKU(sku_name, sku_tier)

    def set_capacity(self, new_capacity):
        self.capacity = new_capacity
    
    def submit(self, judge_request : JudgeRequest):
        judge_request.result = 'ABC'
        with judge_request.fulfilled:
            judge_request.fulfilled.notifyAll()

