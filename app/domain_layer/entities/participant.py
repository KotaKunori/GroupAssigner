from pydantic import BaseModel
from enum import Enum

from ..value_objects.participant_id import ParticipantId
from ..value_objects.participant_name import ParticipantName
from ..value_objects.laboratory_name import LaboratoryName

class PositionType(Enum):
    FACULTY = "Faculty"
    DOCTORAL = "Doctoral"
    MASTER = "Master"
    BACHELOR = "Bachelor"

    @staticmethod
    def value_of(value: str) -> 'PositionType':
        for position in PositionType:
            if position.value == value:
                return position
        raise PositionTypeError(f"Invalid position type: {value}")

    def as_str(self) -> str:
        return self.value
    
class PositionTypeError(Exception):
    """
    Exception raised when the position type is invalid.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"PositionTypeError: {self.message}"

class Participant(BaseModel):
    """
    Domain object of Participant.
    """
    id: ParticipantId
    name: ParticipantName
    position: PositionType
    lab: LaboratoryName

    @staticmethod
    def of(id: ParticipantId, name: ParticipantName, position: PositionType, lab: LaboratoryName) -> 'Participant':
        return Participant(id=id, name=name, position=position, lab=lab)
    
    @staticmethod
    def create(name: ParticipantName, position: PositionType, lab: LaboratoryName) -> 'Participant':
        return Participant(id=ParticipantId.generate(), name=name, position=position, lab=lab)
    
    def get_id(self) -> ParticipantId:
        return self.id
    
    def get_name(self) -> ParticipantName:
        return self.name
    
    def get_position(self) -> PositionType:
        return self.position
    
    def get_lab(self) -> LaboratoryName:
        return self.lab

    def as_str(self) -> str:
        return f"Participant {self.id}: {self.name}"
    
    def convert_to_json(self) -> dict:
        return {
            "id": self.id.as_str(),
            "name": self.name.as_str(),
            "position": self.position.as_str(),
            "lab": self.lab.as_str()
        }
    
    def __eq__(self, other: 'Participant') -> bool:
        if not isinstance(other, Participant):
            return False
        return self.id == other.id