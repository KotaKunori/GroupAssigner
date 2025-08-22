from dataclasses import dataclass

from ...domain_layer.entities.session import Session
from ...domain_layer.value_objects.session_id import SessionId

@dataclass(frozen=True)
class Sessions:
    """
    Class representing a collection of sessions.
    """
    sessions: list[Session]

    @staticmethod
    def of(sessions: list[Session]) -> 'Sessions':
        return Sessions(sessions)

    @staticmethod
    def empty() -> 'Sessions':
        return Sessions({})
    
    def __iter__(self):
        return iter(self.sessions)
    
    # def create_iterator(self, index: int = 0, step: int = 1) -> 'SessionsIterator':
    #     return SessionsIterator(self, index, step, len(self.sessions))

    def add_session(self, session: Session) -> 'Sessions':
        new_sessions = list(self.sessions)
        if session in new_sessions:
            raise SessionExistsError(f"Session {session.id.as_str()} already exists.")
        new_sessions.append(session)
        return Sessions.of(new_sessions)

    def get_session(self, session_id: SessionId) -> Session:
        for session in self.sessions:
            if session.get_id() == session_id:
                return session
        raise SessionNotFoundError(f"Session {session_id.as_str()} not found.")
    
    def get_session_by_index(self, index: int) -> Session:
        if index < 0 or index >= len(self.sessions):
            raise IndexError("Index out of range.")
        return self.sessions[index]

    def remove_session(self, session_id: SessionId) -> 'Sessions':
        new_sessions = [s for s in self.sessions if s.id != session_id]
        if len(new_sessions) == len(self.sessions):
            raise SessionNotFoundError(f"Session {session_id.as_str()} not found.")
        return Sessions.of(new_sessions)

    def length(self) -> int:
        return len(self.sessions)

    def convert_to_json(self) -> list[dict]:
        return [session.convert_to_json() for session in self.sessions]
    
# class SessionsIterator:
#     """
#     Iterator for the Sessions class.
#     """
#     def __init__(self, sessions: Sessions, index: int, step: int, end: int):
#         self.sessions = sessions
#         self.index = index
#         self.step = step
#         self.end = end

#     def has_next(self) -> bool:
#         return self.index < self.end
    
#     def next(self) -> Session:
#         if not self.has_next():
#             raise StopIteration("No more sessions to iterate.")
#         session = self.sessions.get_session_by_index(self.index)
#         self.index += self.step
#         return session
    
#     def get_index(self) -> int:
#         return self.index

class SessionExistsError(Exception):
    """
    Exception raised when a session already exists.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"SessionExistsError: {self.message}"
    
class SessionNotFoundError(Exception):
    """
    Exception raised when a session is not found.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"SessionNotFoundError: {self.message}"