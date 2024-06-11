from enum import Enum


class MachineType:
    """
    A type of machine, see https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/overview.
    """
    # TODO: if possible, decouple this from Azure-specific machine types
    name: str
    tier: str

    def __init__(self, name: str, tier: str):
        self.name = name
        self.tier = tier
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MachineType):
            return False
        return self.name == value.name and self.tier == value.tier

    def __hash__(self) -> int:
        return hash((self.name, self.tier))

    @staticmethod
    def from_name(name: str):
        parts = name.split('_', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid MachineType name format `{name}`")

        return MachineType(name=name, tier=parts[0])

class ResourceSpecification:
    """
    The specification of allocated resources to evaluate a submission.
    """
    num_cpu: int
    num_memory: int
    num_gpu: int
    machine_type: 'MachineType'

    def __init__(self, num_cpu: int, num_memory: int, num_gpu: int, machine_type: 'MachineType'):
        self.num_cpu = num_cpu
        self.num_memory = num_memory # in MB
        self.num_gpu = num_gpu
        self.machine_type = machine_type

class SubmissionType(Enum):
    """
    The type of a submission: either code, or solution.
    """
    CODE = 1
    SOLUTION = 2


class Submission:
    """
    A submission that should be evaluated.
    """
    type: 'SubmissionType'
    source_url: str

    def __init__(self, type: 'SubmissionType', source_url: str):
        self.type = type
        self.source_url = source_url

class JudgeRequest:
    """
    A request for a submission to be evaluated according to some resource specification.
    """
    submission: 'Submission'
    resource_specification: 'ResourceSpecification'

    def __init__(self, submission: 'Submission', resource_specification: 'ResourceSpecification'):
        self.submission = submission
        self.resource_specification = resource_specification

class JudgeResult:
    """
    The result of evaluation by a judge.

    Formatted in JSON.
    """
    result: str
    
    def __init__(self, result: str):
        self.result = result
