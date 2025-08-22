# Moved from app/app.py to avoid name clash with package name when running CLI
from flask import Flask
import json

from .presentation_layer.input_converter.get_groups_params_converter import GetGroupsParamsConverter
from .infrastructure_layer.domain_implementations.group_assinger_ga import GroupAssignerGA
from .domain_layer.first_class_collections.groups import Groups

app = Flask(__name__)

@app.route("/")
def index():
    return "index page"

@app.route("/group_assignment", methods=["GET"])
def assing_groups():
    try:
        # Keep same sample payload as before
        data = {
            "participants": [],
            "sessions": [],
        }
        params = GetGroupsParamsConverter.convert_json_to_params(data)
        groups: dict[int, Groups] = GroupAssignerGA().assign_groups(params.program)
        program = []
        for key, value in groups.items():
            session = []
            for group in value:
                members = []
                for participant in group.get_participants():
                    members.append(participant.get_name().as_str())
                session.append(members)
            program.append(session)
        groups_dict = {"program": program}
        return groups_dict
    except Exception as e:
        raise e

if __name__ == "__main__":
    app.run(debug=True)


