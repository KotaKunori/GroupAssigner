from ..usecases.get_groups_usecase import GetGroupsUseCase
from ...domain_layer.services.group_assigner import GroupAssigner
from ...domain_layer.services.evaluation_algorithm import EvaluationAlgorithm


class GetGroupsUseCaseFactory:
    """GetGroupsUseCaseのファクトリークラス"""
    
    @staticmethod
    def create(
        group_assigner: GroupAssigner,
        evaluation_algorithm: EvaluationAlgorithm
    ) -> GetGroupsUseCase:
        """GetGroupsUseCaseのインスタンスを作成"""
        return GetGroupsUseCase(
            group_assigner=group_assigner,
            evaluation_algorithm=evaluation_algorithm
        )
