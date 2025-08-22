from dataclasses import dataclass

@dataclass(frozen=True)
class ParticipantName:
    """
    Class representing a participant's name.
    """
    value: str

    def as_str(self) -> str:
        return self.value
    
    def __str__(self) -> str:
        return 'Participant Name: ' + self.value
    
    def __eq__(self, other: "ParticipantName") -> bool:
        return self.value == other.value
    
    @staticmethod
    def of(value: str) -> "ParticipantName":
        if not value:
            raise ParticipantNameEmptyError("Participant name cannot be empty.")
        return ParticipantName(value)
    
class ParticipantNameEmptyError(Exception):
    """
    Exception raised when the participant name is empty.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"ParticipantNameEmptyError: {self.message}"
    