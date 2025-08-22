from dataclasses import dataclass

@dataclass(frozen=True)
class LaboratoryName:
    """
    Class representing a participant's name.
    """
    value: list[str]

    def as_str(self) -> str:
        return ', '.join(self.value)
    
    def __str__(self) -> str:
        return 'Participant Name: ' + ', '.join(self.value)
    
    def __eq__(self, other: "LaboratoryName") -> bool:
        for name in self.value:
            if name not in other.value:
                return False
        return True
    
    def __iter__(self):
        return iter(self.value)
    
    def __len__(self):
        return len(self.value)
    
    @staticmethod
    def of(value: list[str]) -> "LaboratoryName":
        if len(value) == 0:
            raise LaboratoryNameEmptyError("Laboratory name cannot be empty.")
        return LaboratoryName(value)
    
class LaboratoryNameEmptyError(Exception):
    """
    Exception raised when the laboratory name is empty.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"LaboratoryNameEmptyError: {self.message}"
    