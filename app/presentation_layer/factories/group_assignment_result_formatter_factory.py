from ..output_formatter.group_assignment_result_formatter import GroupAssignmentResultFormatter
from ...domain_layer.services.evaluation_algorithm import TheoreticalMinCalculator, DistinctPartnersCalculator


class GroupAssignmentResultFormatterFactory:
    """GroupAssignmentResultFormatterのファクトリークラス"""
    
    @staticmethod
    def create() -> GroupAssignmentResultFormatter:
        """GroupAssignmentResultFormatterのインスタンスを作成"""
        theoretical_min_calculator = TheoreticalMinCalculator()
        distinct_partners_calculator = DistinctPartnersCalculator()
        
        return GroupAssignmentResultFormatter(
            theoretical_min_calculator=theoretical_min_calculator,
            distinct_partners_calculator=distinct_partners_calculator
        )
