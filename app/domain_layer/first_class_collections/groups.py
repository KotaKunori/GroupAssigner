from dataclasses import dataclass

from ..entities.group import Group
from ..value_objects.group_id import GroupId

@dataclass(frozen=True)
class Groups:
    """
    Class representing a collection of groups.
    """
    groups: list[Group]

    @staticmethod
    def of(groups: list[Group]) -> 'Groups':
        return Groups(groups)

    @staticmethod
    def empty() -> 'Groups':
        return Groups([])
    
    def __iter__(self):
        return iter(self.groups)
    
    # def create_iterator(self, index: int = 0, step: int = 1) -> 'GroupsIterator':
    #     return GroupsIterator(self, index, step, len(self.groups))

    def add_group(self, group: Group) -> 'Groups':
        new_groups = list(self.groups)
        if group in new_groups:
            raise GroupsExistsError(f"Group {group.id.as_str()} already exists.")
        new_groups.append(group)
        return Groups.of(new_groups)

    def get_group(self, group_id: GroupId) -> Group:
        for group in self.groups:
            if group.id == group_id:
                return group
        raise GroupsNotFoundError(f"Group {group_id.as_str()} not found.")
    
    def get_group_by_index(self, index: int) -> Group:
        if index < 0 or index >= len(self.groups):
            raise IndexError("Index out of range.")
        return self.groups[index]

    def remove_group(self, group_id: GroupId) -> 'Groups':
        new_groups = [g for g in self.groups if g.id != group_id]
        if len(new_groups) == len(self.groups):
            raise GroupsNotFoundError(f"Group {group_id.as_str()} not found.")
        return Groups.of(new_groups)

    def length(self) -> int:
        return len(self.groups)

    def convert_to_json(self) -> list[dict]:
        return [group.convert_to_json() for group in self.groups]
    
# class GroupsIterator:
#     """
#     Iterator for the Groups class.
#     """
#     def __init__(self, groups: Groups, index: int, step: int, end: int):
#         self.groups = groups
#         self.index = index
#         self.step = step
#         self.end = end

#     def has_next(self) -> bool:
#         return self.index < self.end
    
#     def next(self) -> Group:
#         if not self.has_next():
#             raise StopIteration("No more groups to iterate.")
#         group = self.groups.get_group_by_index(self.index)
#         self.index += self.step
#         return group
    
    def get_index(self) -> int:
        return self.index
    
class GroupsExistsError(Exception):
    """
    Exception raised when a group already exists in the collection.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"GroupsExistsError: {self.message}"
    
class GroupsNotFoundError(Exception):
    """
    Exception raised when a group is not found in the collection.
    """
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"GroupsNotFoundError: {self.message}"