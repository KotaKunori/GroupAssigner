from abc import ABC, abstractmethod

from ...domain_layer.member import Member, Members

class MemberRepository(ABC):
    @abstractmethod
    def find_all(self) -> Members:
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def find_by_id(self, member_id: int) -> Member:
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def store(self, member):
        raise NotImplementedError("This method should be overridden by subclasses.")