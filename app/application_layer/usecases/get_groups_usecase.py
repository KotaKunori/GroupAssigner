from typing import Dict
from ..input_params.get_groups_params import GetGroupsParams
from ...domain_layer.entities.program import Program
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.services.evaluation_algorithm import EvaluationAlgorithm
from ...domain_layer.services.group_assigner import GroupAssigner


class GetGroupsUseCase:
    """グループ割り当てと評価を実行するユースケース"""
    
    def __init__(
        self,
        group_assigner: GroupAssigner,
        evaluation_algorithm: EvaluationAlgorithm
    ):
        self._group_assigner = group_assigner
        self._evaluation_algorithm = evaluation_algorithm
    
    def execute(self, params: GetGroupsParams) -> Dict[str, any]:
        """グループ割り当てを実行し、結果を評価して返す"""
        # グループ割り当てを実行
        groups: Dict[int, Groups] = self._group_assigner.assign_groups(params.program)
        
        # 評価スコアを計算
        score = self._evaluation_algorithm.evaluate(groups)
        
        # 結果を返す
        return {
            "groups": groups,
            "evaluation_score": score
        }
        