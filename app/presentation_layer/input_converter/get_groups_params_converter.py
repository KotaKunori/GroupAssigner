from ...application_layer.input_params.get_groups_params import GetGroupsParams

from ...application_layer.factories.participant_factory import ParticipantFactory
from ...domain_layer.first_class_collections.participants import Participants
from ...domain_layer.first_class_collections.sessions import Sessions
from ...domain_layer.entities.session import Session
from ...domain_layer.entities.program import Program

class GetGroupsParamsConverter:
    @staticmethod
    def convert_json_to_params(params) -> GetGroupsParams:
        try:
            # Check if params is None
            if params is None:
                raise MissingParameterError("Missing parameter: params")
            
            # Check if params has the required attributes
            if "participants" not in params or params["participants"] is None:
                raise MissingParameterError("Missing parameter: participants")
            if "sessions" not in params or params["sessions"] is None:
                raise MissingParameterError("Missing parameter: sessions")
            
            if not isinstance(params["participants"], list):
                raise AttributeTypeError("Attribute participants must be a list")
            if not isinstance(params["sessions"], list):
                raise AttributeTypeError("Attribute sessions must be an list")
            
            participants = Participants.empty()
            for participant_dict in params["participants"]:
                participant = ParticipantFactory.create_participant(participant_dict)
                participants = participants.add_participant(participant)

            sessions = Sessions.empty()
            for session_dict in params["sessions"]:
                if "group_num" not in session_dict or session_dict["group_num"] is None:
                    raise AttributeNotFoundError("Attribute group_num not found in session")
                if "min" not in session_dict or session_dict["min"] is None:
                    raise AttributeNotFoundError("Attribute min not found in session")
                if "max" not in session_dict or session_dict["max"] is None:
                    raise AttributeNotFoundError("Attribute max not found in session")
                session = Session.create(group_num=session_dict["group_num"], min=session_dict["min"], max=session_dict["max"], participants=participants)
                sessions = sessions.add_session(session)

            program = Program.create(
                participants=participants,
                sessions=sessions
            )
            return GetGroupsParams.of(program=program)
            
        except Exception as e:
            raise e

class MissingParameterError(Exception):
    """
    Exception raised when a required parameter is missing.
    """
    def __init__(self, message: str):
        super().__init__(self.message)

class AttributeNotFoundError(Exception):
    """
    Exception raised when a required attribute is missing.
    """
    def __init__(self, message: str):
        super().__init__(self.message)

class AttributeTypeError(Exception):
    """
    Exception raised when a required attribute is missing.
    """
    def __init__(self, message: str):
        super().__init__(self.message)