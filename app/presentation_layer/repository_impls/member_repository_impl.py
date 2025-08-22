import json

from ...application_layer.repository_interfaces.member_repository import MemberRepository

from ...domain_layer.member import Attribute, Attributes, Member, Members


PATH = "app/members.json"

class MemberRepositoryImpl(MemberRepository):

    def __init__(self, members: Members):
        self.members = members

    @staticmethod
    def of():
        members = Members.empty()
        try:
            data = MemberRepositoryImpl.read_json()
            if data is None:
                raise ValueError("Input cannot be None")
            if not isinstance(data, dict):
                raise ValueError("Input must be a dictionary")
            if 'members' not in data:
                raise ValueError("Input must contain 'members' key")
            if not isinstance(data['members'], list):
                raise ValueError("'members' must be a list")
            members_json: list[dict] = data.get('members')
            count = 0
            for member_json in members_json:
                if not isinstance(member_json, dict):
                    raise ValueError("Each member must be a dictionary")
                attributes: Attributes = Attributes.empty()
                for key in member_json.keys():
                    if not isinstance(key, str):
                        raise ValueError("Member ID must be a string")
                    attributes = attributes.add_attribute(Attribute.of(key, member_json[key]))
                member: Member = Member.of(count, attributes)
                members: Members = members.add_member(member)
                count += 1
        except ValueError as e:
            raise ValueError(f"Invalid input: {e}")
        
        return MemberRepositoryImpl(members)

    @staticmethod
    def read_json():
        with open(PATH, 'r') as file:
            data = json.load(file)
        return data
    
    @staticmethod
    def write_json(data):
        with open(PATH, 'w') as file:
            json.dump(data, file)

    def find_all(self) -> Members:
        return self.members
    
    def find_by_id(self, member_id) -> Member:
        return self.members.get_member(member_id)
    
    def store(self, member: Member):
        new_members = self.members.add_member(member)
        self.members = new_members
        MemberRepositoryImpl.write_json(self.members.convert_to_json())
        