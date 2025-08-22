from dataclasses import dataclass
from ...infrastructure_layer.helper.ulid_helper import ULIDHelper

GROUP_ID_PREFIX = 'group'

@dataclass(frozen=True)
class GroupId:
    value: str

    def as_str(self) -> str:
        return GROUP_ID_PREFIX + '-' + self.value
    
    def __str__(self) -> str:
        return 'Group Id: ' + self.value
    
    def __eq__(self, other: "GroupId") -> bool:
        self_value = self.value
        if self.value.startswith(GROUP_ID_PREFIX + '-'):
            self_value = self.value[len(GROUP_ID_PREFIX) + 1:]
        other_value = other.value
        if other.value.startswith(GROUP_ID_PREFIX + '-'):
            other_value = other.value[len(GROUP_ID_PREFIX) + 1:]
        return self_value == other_value
    
    @staticmethod
    def of(value: str) -> "GroupId":
        if value.startswith(GROUP_ID_PREFIX + '-'):
            value = value[len(GROUP_ID_PREFIX) + 1:]
        if not ULIDHelper.validate(value):
            raise GroupIdValidationError(f"Invalid GroupId: {value}")
        return GroupId(value)
    
    @staticmethod
    def generate() -> "GroupId":
        return GroupId.of(str(ULIDHelper.generate()))
    
class GroupIdValidationError(Exception):
    """
    Custom exception for GroupId validation errors.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"GroupIdValidationError: {self.message}"