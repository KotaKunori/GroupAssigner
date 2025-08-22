from dataclasses import dataclass

from ..entities.participant import Participant
from ..value_objects.participant_id import ParticipantId

@dataclass(frozen=True)
class Participants:
    """
    Class representing a collection of participants.
    """
    participants: list[Participant]

    @staticmethod
    def of(participants: list[Participant]) -> 'Participants':
        return Participants(participants)
    
    @staticmethod
    def empty() -> 'Participants':
        return Participants([])
    
    def __iter__(self):
        return iter(self.participants)

    # def create_iterator(self, index: int = 0, step: int = 1) -> 'ParticipantsIterator':
    #     return ParticipantsIterator(self, index, step, len(self.participants))
    
    def get_ids(self) -> list[ParticipantId]:
        return [participant.id for participant in self.participants]

    def add_participant(self, participant: Participant) -> 'Participants':
        new_participants = list(self.participants)
        if participant in new_participants:
            raise PariticipantsExistsError(f"Participant {participant.id.as_str()} already exists.")
        new_participants.append(participant)
        return Participants.of(new_participants)
    
    def get_participant(self, participant_id: ParticipantId) -> Participant:
        for participant in self.participants:
            if participant.id == participant_id:
                return participant
        raise ParticipantsNotFoundError(f"Participant {participant_id.as_str()} not found.")
    
    def get_participant_by_index(self, index: int) -> Participant:
        if index < 0 or index >= len(self.participants):
            raise IndexError("Index out of range.")
        return self.participants[index]
    
    def remove_participant(self, participant_id: ParticipantId) -> 'Participants':
        new_participants = [p for p in self.participants if p.id != participant_id]
        if len(new_participants) == len(self.participants):
            raise ParticipantsNotFoundError(f"Participant {participant_id.as_str()} not found.")
        return Participants.of(new_participants)
    
    def length(self) -> int:
        return len(self.participants)
    
    def convert_to_json(self) -> list[dict]:
        return [participant.convert_to_json() for participant in self.participants]
    
# class ParticipantsIterator:
#     """
#     Iterator for the Participants class.
#     """
#     def __init__(self, participants: Participants, index: int, step: int, end: int):
#         self.participants = participants
#         self.index = index
#         self.step = step
#         self.end = end
    
#     def has_next(self) -> bool:
#         return self.index < self.end
    
#     def next(self) -> Participant:
#         if not self.has_next():
#             raise IndexError("No more participants.")
#         participant = self.participants.get_participant_by_index(self.index)
#         self.index += self.step
#         return participant
    
#     def get_index(self) -> int:
#         return self.index
    
class PariticipantsExistsError(Exception):
    """
    Exception raised when a participant already exists in the collection.
    """
    def __init__(self, message: str):
        super().__init__(message)
    
    def __str__(self) -> str:
        return f"ParticipantsExistsError: {self.message}"
    
class ParticipantsNotFoundError(Exception):
    """
    Exception raised when a participant is not found in the collection.
    """
    def __init__(self, message: str):
        super().__init__(message)
    
    def __str__(self) -> str:
        return f"ParticipantsNotFoundError: {self.message}"