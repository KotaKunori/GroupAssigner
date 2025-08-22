from dataclasses import dataclass
from ...infrastructure_layer.helper.ulid_helper import ULIDHelper

PARTICIPANT_ID_PREFIX = 'participant'

@dataclass(frozen=True)
class ParticipantId:
    value: str

    def as_str(self) -> str:
        return PARTICIPANT_ID_PREFIX + '-' + self.value
    
    def __str__(self) -> str:
        return 'Participant Id: ' + self.value
    
    def __eq__(self, other: "ParticipantId") -> bool:
        self_value = self.value
        if self.value.startswith(PARTICIPANT_ID_PREFIX + '-'):
            self_value = self.value[len(PARTICIPANT_ID_PREFIX) + 1:]
        other_value = other.value
        if other.value.startswith(PARTICIPANT_ID_PREFIX + '-'):
            other_value = other.value[len(PARTICIPANT_ID_PREFIX) + 1:]
        return self_value == other_value
    
    @staticmethod
    def of(value: str) -> "ParticipantId":
        if value.startswith(PARTICIPANT_ID_PREFIX + '-'):
            value = value[len(PARTICIPANT_ID_PREFIX) + 1:]
        if not ULIDHelper.validate(value):
            raise ParticipantIdValidationError(f"Invalid ParticipantId: {value}")
        return ParticipantId(value)
    
    @staticmethod
    def generate() -> "ParticipantId":
        return ParticipantId.of(str(ULIDHelper.generate()))
    
class ParticipantIdValidationError(Exception):
    """
    Custom exception for ParticipantId validation errors.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"ParticipantIdValidationError: {self.message}"