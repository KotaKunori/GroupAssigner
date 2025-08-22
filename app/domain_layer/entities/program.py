from pydantic import BaseModel

from ..value_objects.program_id import ProgramId
from ..first_class_collections.participants import Participants
from ..first_class_collections.sessions import Sessions

class Program(BaseModel):
    """
    Domain object of Program.
    """

    id: ProgramId
    participants: Participants
    sessions: Sessions

    @staticmethod
    def of(id: ProgramId, participants: Participants, sessions: Sessions) -> 'Program':
        return Program(id=id, participants=participants, sessions=sessions)
    
    @staticmethod
    def create(participants: Participants, sessions: Sessions) -> 'Program':
        return Program(id=ProgramId.generate(), participants=participants, sessions=sessions)
    
    def get_id(self) -> ProgramId:
        return self.id
    
    def get_participants(self) -> Participants:
        return self.participants
    
    def get_sessions(self) -> Sessions:
        return self.sessions
        
    def convert_to_json(self) -> dict:
        return {
            "id": self.id.as_str(),
            "participants": self.participants.convert_to_json(),
            "sessions": self.sessions.convert_to_json()
        }