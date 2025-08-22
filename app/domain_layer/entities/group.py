from pydantic import BaseModel

from ..first_class_collections.participants import Participants
from ..value_objects.group_id import GroupId

class Group(BaseModel):
    """
    Class representing a group of participants.
    """
    
    id: GroupId
    participants: Participants

    @staticmethod
    def of(id: GroupId, participants: Participants) -> 'Group':
        return Group(id=id, participants=participants)
    
    @staticmethod
    def create(participants: Participants) -> 'Group':
        return Group(id=GroupId.generate(), participants=participants)
    
    def get_id(self) -> GroupId:
        return self.id
    
    def get_participants(self) -> Participants:
        return self.participants
    
    def as_str(self) -> str:
        return f"Group {self.id}: {self.participants}"
    
    def convert_to_json(self) -> dict:
        return {
            "id": self.id.as_str(),
            "participants": self.participants.convert_to_json()
        }