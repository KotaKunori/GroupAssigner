import json
from typing import Dict, Any
from pathlib import Path
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.services.evaluation_algorithm import TheoreticalMinCalculator, DistinctPartnersCalculator


class GroupAssignmentResultFormatter:
    """グループ割り当て結果を整形するクラス"""
    
    def __init__(self, theoretical_min_calculator: TheoreticalMinCalculator, distinct_partners_calculator: DistinctPartnersCalculator):
        self._theoretical_min_calculator = theoretical_min_calculator
        self._distinct_partners_calculator = distinct_partners_calculator
    
    def format_result(self, groups: Dict[int, Groups], program, evaluation_score: float) -> Dict[str, Any]:
        """結果を整形して辞書形式で返す"""
        # 理論最小値を計算
        theo_min = self._theoretical_min_calculator.calculate_theoretical_min_avg_repeat(program)
        
        # 各人が同じグループになった「異なる人の数」を集計
        partners_summary = self._distinct_partners_calculator.calculate_distinct_partners(groups)
        
        # 詳細なパートナー統計を計算
        partner_stats_raw = self._distinct_partners_calculator.calculate_partner_statistics(groups)
        
        # フォーマットを "distinct_partners/total_partners/duplicate_partners" に変換
        partner_stats = {}
        for name, stats in partner_stats_raw.items():
            partner_stats[name] = f"{stats['distinct_partners']}/{stats['total_partners']}/{stats['duplicate_partners']}"
        
        # ラボ重複統計を計算
        lab_overlap_stats = self._distinct_partners_calculator.calculate_lab_overlap_statistics(groups)
        
        # プログラムの整形
        program_out = []
        for key, value in groups.items():
            session = []
            for group in value:
                members = []
                for participant in group.get_participants():
                    members.append(f"{participant.get_name().as_str()}({participant.get_position().as_str()})")
                session.append(members)
            program_out.append(session)
        
        return {
            "program": program_out,
            "evaluation": {
                "avg_repeat_per_person": evaluation_score,
                "theoretical_min_avg_repeat": theo_min,
                "distinct_partners_per_person": partners_summary,
                "partner_statistics": partner_stats,
                "lab_overlap_statistics": lab_overlap_stats
            }
        }
    
    def format_for_console(self, result: Dict[str, Any]) -> str:
        """コンソール出力用に整形"""
        output = json.dumps(result, ensure_ascii=False, indent=2)
        output += f"\n評価値(avg_repeat_per_person): {result['evaluation']['avg_repeat_per_person']}"
        output += f"\n理論最小値(theoretical_min_avg_repeat): {result['evaluation']['theoretical_min_avg_repeat']}"
        
        # ラボ重複統計の要約
        lab_stats = result['evaluation']['lab_overlap_statistics']
        total_overlaps = sum(stats['lab_overlap_count'] for stats in lab_stats.values())
        avg_overlaps = total_overlaps / len(lab_stats) if lab_stats else 0
        output += f"\nラボ重複統計: 総数={total_overlaps}, 平均={avg_overlaps:.2f}"
        
        return output
    
    def save_to_file(self, result: Dict[str, Any], file_path: Path) -> None:
        """結果をファイルに保存"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
