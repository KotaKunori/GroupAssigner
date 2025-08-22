from pydantic import BaseModel

from ..value_objects.session_id import SessionId
from ..first_class_collections.participants import Participants

class Session(BaseModel):
    """
    Domain object of Session.
    """

    id: SessionId
    group_num: int
    min: int
    max: int
    participants: Participants

    @staticmethod
    def of(id: SessionId, group_num: int, min: int, max: int, participants: Participants) -> 'Session':
        return Session(id=id, group_num=group_num, min=min, max=max, participants=participants)
    
    @staticmethod
    def create(group_num: int, min: int, max: int, participants: Participants) -> 'Session':
        return Session(id=SessionId.generate(), group_num=group_num, min=min, max=max, participants=participants)

    def get_id(self) -> SessionId:
        return self.id
    
    def get_participants(self) -> Participants:
        return self.participants
    
    def get_group_num(self) -> int:
        return self.group_num

    def get_min(self) -> int:
        return self.min
    
    def get_max(self) -> int:
        return self.max
    
    def get_max_group_range(self) -> range:
        # Use the configured number of groups as the group index range
        return range(self.group_num)
    
    def convert_to_json(self) -> dict:
        return {
            "id": self.id.as_str(),
            "participants": self.participants.convert_to_json(),
        }