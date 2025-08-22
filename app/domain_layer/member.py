from dataclasses import dataclass

@dataclass
class Attribute:
    name: str
    value: str

    @staticmethod
    def of(name: str, value: str) -> 'Attribute':
        return Attribute(name, value)

    def __eq__(self, other: 'Attribute') -> bool:
        if not isinstance(other, Attribute):
            return False
        return self.name == other.name and self.value == other.value
    
    def get_name(self) -> str:
        return self.name
    
    def get_value(self) -> str:
        return self.value

    def as_str(self) -> str:
        return f"{self.name}: {self.value}"
    
    def convert_to_json(self) -> dict[str, str]:
        return {self.name: self.value}
    
@dataclass
class Attributes:
    attributes: dict[str, Attribute]

    @staticmethod
    def of(attributes: dict[str, str]) -> 'Attributes':
        return Attributes(attributes)

    @staticmethod
    def empty() -> 'Attributes':
        return Attributes({})

    def add_attribute(self, attribute: Attribute) -> 'Attributes':
        new_attributes = dict(self.attributes)
        if attribute.name in new_attributes:
            raise ValueError(f"Attribute with name {attribute.name} already exists.")
        new_attributes[attribute.name] = attribute
        return Attributes(new_attributes)

    def get_attribute(self, name: str) -> Attribute:
        if name not in self.attributes:
            raise ValueError(f"Attribute with name {name} does not exist.")
        return self.attributes.get(name)
    
    def get_value(self, name: str) -> str:
        if name not in self.attributes:
            raise ValueError(f"Attribute with name {name} does not exist.")
        return self.attributes[name].get_value()
    
    def as_str(self) -> str:
        return ', '.join([f"{attr.as_str()}" for attr in self.attributes.values()])
    
    def convert_to_json(self) -> dict[str, str]:
        json = {}
        for attr in self.attributes.values():
            json.update(attr.convert_to_json())
        return json

@dataclass
class Member:
    id: int
    attributes: Attributes

    @staticmethod
    def of(id: int, attributes: Attributes) -> 'Member':
        return Member(id, attributes)

    def as_str(self) -> str:
        return f"Member {self.id}: {self.attributes.as_str()}"
    
    def convert_to_json(self) -> dict:
        json = {"id": self.id}
        json.update(self.attributes.convert_to_json())
        return json
    
    def get_value(self, name: str) -> str:
        return self.attributes.get_value(name)
        

@dataclass
class Members:
    members: dict[int, Member]

    @staticmethod
    def of(members: dict[int, Member]) -> 'Members':
        return Members(members)
    
    def empty() -> 'Members':
        return Members({})

    def add_member(self, member: Member) -> 'Members':
        if member.id in self.members:
            raise ValueError(f"Member with id {member.id} already exists.")
        new_members = dict(self.members)
        new_members[member.id] = member
        return Members(new_members)

    def get_member(self, member_id: int) -> Member:
        return self.members.get(member_id)

    def as_str(self) -> str:
        return ', '.join([f"{member.as_str()}" for member in self.members.values()])
    
    def convert_to_json(self) -> list[dict]:
        return [member.convert_to_json() for member in self.members.values()]
    
    def get_keys(self) -> list[int]:
        return list(self.members.keys())
    
    def length(self) -> int:
        return len(self.members)
    
    def create_iterator(self) -> 'MembersIterator':
        return MembersIterator(self)
    
class MembersIterator:
    def __init__(self, members: Members):
        self.members = members
        self.index = 0
        self.step = 1
        self.end = members.length()

    def has_next(self) -> bool:
        return self.index < self.end
    
    def next(self) -> Member:
        output_key = self.members.get_keys()[self.index]
        self.index += self.step
        return self.members.get_member(output_key)