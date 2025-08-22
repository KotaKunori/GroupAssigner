from dataclasses import dataclass

from ...domain_layer.entities.program import Program

@dataclass
class GetGroupsParams:
    """
    Parameters for getting groups.
    """
    program: Program

    @staticmethod
    def of(program: Program) -> 'GetGroupsParams':
        return GetGroupsParams(program)