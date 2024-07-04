
from mock.mock_vm import MockVM


class MockSKU:
    def __init__(self, name, tier):
        self.name = name
        self.tier = tier
        self.capacity = 0

class MockVMSS():
    name: str
    sku: MockSKU

    vms = {}

    def __init__(self, sku_name, sku_tier):
        self.name = ""
        self.sku = MockSKU(sku_name, sku_tier)

    def set_capacity(self, new_capacity):
        diff = new_capacity - self.sku.capacity
        print(f'capaicty: {new_capacity} diff: {diff}')
        
        if diff > 0:
            if len(self.vms.keys()) == 0:
                key = 0
            else:
                key = max([int(i) for i in self.vms.keys()])
            for i in range(diff):
                self.vms[str(i + key + 1)] = MockVM(str(i + key + 1))
        self.sku.capacity = new_capacity

    def list_vms(self):
        return self.vms.values()
    
    def get_vm_dict(self):
        return self.vms
    
    def clean_up(self):
        self.vms = {}
        return

