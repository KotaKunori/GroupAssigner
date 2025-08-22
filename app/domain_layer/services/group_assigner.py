from abc import ABC, abstractmethod
from typing import Dict

from ..entities.program import Program
from ..first_class_collections.groups import Groups

class GroupAssigner(ABC):
    @abstractmethod
    def assign_groups(self, program: Program) -> Dict[int, Groups]:
        """
        Assign groups to the program.
        Returns a dictionary mapping session index to Groups.
        """
        pass
