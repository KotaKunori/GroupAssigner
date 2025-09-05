import json
import sys
import re
from collections import defaultdict
from typing import Any
from pathlib import Path

from app.infrastructure_layer.domain_implementations.group_assinger_ga import GroupAssignerGA
from app.infrastructure_layer.domain_implementations.group_assigner_hybrid_ga import GroupAssignerHybridGA

from .presentation_layer.input_converter.get_groups_params_converter import GetGroupsParamsConverter
from .presentation_layer.factories.group_assignment_result_formatter_factory import GroupAssignmentResultFormatterFactory
# from .infrastructure_layer.domain_implementations.group_assigner_ortools import GroupAssignerORTools
# from .infrastructure_layer.domain_implementations.group_assigner_ortools_advanced import GroupAssignerORToolsAdvanced
# from .infrastructure_layer.domain_implementations.group_assigner_ortools_relaxed import GroupAssignerORToolsRelaxed
from .infrastructure_layer.domain_implementations.group_assigner_heuristic import GroupAssignerHeuristic
from .domain_layer.services.evaluation_algorithm import AverageRepeatEvaluationAlgorithm
from .application_layer.factories.get_groups_usecase_factory import GetGroupsUseCaseFactory
from .presentation_layer.reporting.group_balance_reporter import generate_group_balance_tables, generate_session_group_matrix_csv
from .presentation_layer.output_formatter.result_postprocessor import add_distinct_partners_stats

def main() -> int:
    try:
        # 外部入力ファイルから読み込む
        input_path = Path(__file__).parent / "inputs" / "input.json"
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        params = GetGroupsParamsConverter.convert_json_to_params(data)
        
        # アルゴリズムの選択（コメントアウトを変更して切り替え）
        # 1. ヒューリスティック + GA ハイブリッド（推奨）
        group_assigner = GroupAssignerHybridGA(
            num_heuristic_seeds=10,
            generations=500,
            population_size=40,
            mutation_rate=0.08,
            time_budget_seconds=3.0,
            heuristic_iterations=200,
        )
        # 2. ヒューリスティック
        # group_assigner = GroupAssignerHeuristic(max_iterations=1000)
        
        # 3. OR-Tools制約緩和版
        # group_assigner = GroupAssignerORToolsRelaxed()
        
        # 4. OR-Tools標準版
        # group_assigner = GroupAssignerORTools()
        
        # 5. OR-Tools高度版
        # group_assigner = GroupAssignerORToolsAdvanced()

        # 6. 遺伝的アルゴリズム
        # group_assigner = GroupAssignerGA()
        
        evaluation_algorithm = AverageRepeatEvaluationAlgorithm()
        usecase = GetGroupsUseCaseFactory.create(group_assigner, evaluation_algorithm)
        
        # ユースケースを実行
        result = usecase.execute(params)
        groups = result["groups"]
        evaluation_score = result["evaluation_score"]

        # 結果フォーマッターを作成
        formatter = GroupAssignmentResultFormatterFactory.create()
        
        # 結果を整形
        formatted_result = formatter.format_result(groups, params.program, evaluation_score)
        # 結果の後処理（平均・分散付与）
        add_distinct_partners_stats(formatted_result)
        
        # コンソール出力
        console_output = formatter.format_for_console(formatted_result)
        print(console_output)
        
        # 出力先フォルダを作成し、ファイルに保存
        outputs_dir = Path(__file__).parent / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        out_path = outputs_dir / "result.json"
        formatter.save_to_file(formatted_result, out_path)
        
        # 保存した結果を使って共起テーブルとセッション別グループCSVを生成
        generate_group_balance_tables(str(out_path), outputs_dir)
        generate_session_group_matrix_csv(str(out_path), outputs_dir)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


