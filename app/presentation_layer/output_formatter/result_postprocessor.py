from typing import Dict, Any


def add_distinct_partners_stats(formatted_result: Dict[str, Any]) -> None:
    """formatted_result['evaluation'] に平均と分散を付加する。in-place更新。"""
    evaluation = formatted_result.get("evaluation", {})
    distinct_map = evaluation.get("distinct_partners_per_person", {})
    counts = list(distinct_map.values())
    if not counts:
        return
    mean_val = sum(counts) / len(counts)
    var_val = sum((c - mean_val) ** 2 for c in counts) / len(counts)
    evaluation["distinct_partners_avg"] = mean_val
    evaluation["distinct_partners_variance"] = var_val
    formatted_result["evaluation"] = evaluation


