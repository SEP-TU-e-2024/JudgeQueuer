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
    validator_url: str

    def __init__(self, type: 'SubmissionType', source_url: str, validator_url: str):
        self.type = type
        self.source_url = source_url
        self.validator_url = validator_url

class JudgeRequest:
    """
    A request for a submission to be evaluated according to some resource specification.
    """
    submission: 'Submission'
    machine_type: MachineType
    cpus: int
    memory: int # MB
    evaluation_settings: dict
    benchmark_instances: dict[str, str]

    def __init__(self, submission: 'Submission', machine_type: MachineType, cpus: int, memory: int, evaluation_settings: dict, benchmark_instances: dict[str, str]):
        self.submission = submission
        self.machine_type = machine_type
        self.cpus = cpus
        self.memory = memory
        self.evalution_settings = evaluation_settings
        self.benchmark_instances = benchmark_instances

class JudgeResult:
    """
    The result of evaluation by a judge.

    Formatted in JSON.
    """
    result: str
    
    def __init__(self, result: str):
        self.result = result
