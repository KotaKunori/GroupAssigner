from dataclasses import dataclass
from ...infrastructure_layer.helper.ulid_helper import ULIDHelper

SESSION_ID_PREFIX = 'session'

@dataclass(frozen=True)
class SessionId:
    value: str
    def as_str(self) -> str:
        return SESSION_ID_PREFIX + '-' + self.value
    
    def __str__(self) -> str:
        return 'Session Id: ' + self.value
    
    def __eq__(self, other: "SessionId") -> bool:
        self_value = self.value
        if self.value.startswith(SESSION_ID_PREFIX + '-'):
            self_value = self.value[len(SESSION_ID_PREFIX) + 1:]
        other_value = other.value
        if other.value.startswith(SESSION_ID_PREFIX + '-'):
            other_value = other.value[len(SESSION_ID_PREFIX) + 1:]
        return self_value == other_value
    
    @staticmethod
    def of(value: str) -> "SessionId":
        if value.startswith(SESSION_ID_PREFIX + '-'):
            value = value[len(SESSION_ID_PREFIX) + 1:]
        if not ULIDHelper.validate(value):
            raise SessionIdValidationError(f"Invalid SessionId: {value}")
        return SessionId(value)
    
    @staticmethod
    def generate() -> "SessionId":
        return SessionId.of(str(ULIDHelper.generate()))
    
class SessionIdValidationError(Exception):
    """
    Custom exception for SessionId validation errors.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"SessionIdValidationError: {self.message}"