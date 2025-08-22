from dataclasses import dataclass

from ...infrastructure_layer.helper.ulid_helper import ULIDHelper

PROGRAM_ID_PREFIX = 'program'

@dataclass(frozen=True)
class ProgramId:
    value: str

    def as_str(self) -> str:
        return PROGRAM_ID_PREFIX + '-' + self.value
    
    def __str__(self) -> str:
        return 'Program Id: ' + self.value
    
    def __eq__(self, other: "ProgramId") -> bool:
        self_value = self.value
        if self.value.startswith(PROGRAM_ID_PREFIX + '-'):
            self_value = self.value[len(PROGRAM_ID_PREFIX) + 1:]
        other_value = other.value
        if other.value.startswith(PROGRAM_ID_PREFIX + '-'):
            other_value = other.value[len(PROGRAM_ID_PREFIX) + 1:]
        return self_value == other_value
    
    @staticmethod
    def of(value: str) -> "ProgramId":
        if value.startswith(PROGRAM_ID_PREFIX + '-'):
            value = value[len(PROGRAM_ID_PREFIX) + 1:]
        if not ULIDHelper.validate(value):
            raise ProgramIdValidationError(f"Invalid ProgramId: {value}")
        return ProgramId(value)
    
    @staticmethod
    def generate() -> "ProgramId":
        return ProgramId.of(str(ULIDHelper.generate()))
    
class ProgramIdValidationError(Exception):
    """
    Custom exception for ProgramId validation errors.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"ProgramIdValidationError: {self.message}"