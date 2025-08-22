from ...domain_layer.entities.participant import Participant, PositionType

from ...domain_layer.value_objects.participant_name import ParticipantName
from ...domain_layer.value_objects.laboratory_name import LaboratoryName

class ParticipantFactory:
    @staticmethod
    def create_participant(dict) -> Participant:
        """
        Create a Participant object from a dictionary.
        """
        try:
            if "name" not in dict or dict["name"] is None:
                raise ValueError("Missing parameter: name")
            if "position" not in dict or dict["position"] is None:
                raise ValueError("Missing parameter: position")
            if "lab" not in dict or dict["lab"] is None:
                raise ValueError("Missing parameter: lab")
            
            if not isinstance(dict["name"], str):
                raise ValueError("Attribute name must be a string")
            if not isinstance(dict["position"], str):
                raise ValueError("Attribute position must be a string")
            if not isinstance(dict["lab"], list):
                raise ValueError("Attribute lab must be a list of strings")
            return Participant.create(
                ParticipantName.of(dict["name"]),
                PositionType.value_of(dict["position"]),
                LaboratoryName.of(dict["lab"]),
            )
        except ValueError as e:
            raise ValueError(f"Error creating participant: {e}")