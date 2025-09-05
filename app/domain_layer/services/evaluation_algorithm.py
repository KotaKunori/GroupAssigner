from abc import ABC, abstractmethod
from typing import Dict
from ..first_class_collections.groups import Groups
from ..entities.participant import Participant


class EvaluationAlgorithm(ABC):
    """評価アルゴリズムの抽象クラス"""
    
    @abstractmethod
    def evaluate(self, groups_dict: Dict[int, Groups]) -> float:
        """グループ割り当て結果を評価してスコアを返す"""
        pass


class AverageRepeatEvaluationAlgorithm(EvaluationAlgorithm):
    """平均リピート回数を計算する評価アルゴリズム"""
    
    def evaluate(self, groups_dict: Dict[int, Groups]) -> float:
        """各人の (同一相手との同席回数 - 1) の総和を個人スコアとし、その平均を評価値とする"""
        # すべての参加者IDを収集
        all_participants: Dict[str, Participant] = {}
        for _, session_groups in groups_dict.items():
            for group in session_groups:
                for p in group.get_participants():
                    all_participants[p.get_id().as_str()] = p

        # ペア同席回数をカウント
        pair_together: Dict[tuple[str, str], int] = {}
        for _, session_groups in groups_dict.items():
            for group in session_groups:
                ids = [p.get_id().as_str() for p in group.get_participants()]
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        a, b = sorted((ids[i], ids[j]))
                        pair_together[(a, b)] = pair_together.get((a, b), 0) + 1

        # 各人のリピート回数合計（初回は0、それ以降を加算）
        per_person_repeat_sum: Dict[str, int] = {pid: 0 for pid in all_participants.keys()}
        for (a, b), cnt in pair_together.items():
            if cnt > 1:
                per_person_repeat_sum[a] += (cnt - 1)
                per_person_repeat_sum[b] += (cnt - 1)

        if not per_person_repeat_sum:
            return 0.0
        avg = sum(per_person_repeat_sum.values()) / len(per_person_repeat_sum)
        return avg


class TheoreticalMinCalculator:
    """理論最小値を計算するクラス"""
    
    @staticmethod
    def calculate_theoretical_min_avg_repeat(program) -> float:
        """理論最小値（平均）：セッション毎のペア発生数の理論最小合計Qから 2*Q/N - (N-1) を下限として算出"""
        # 参加者数
        sessions = program.get_sessions()
        participants = program.get_participants()
        N = participants.length()
        if N <= 1:
            return 0.0
            
        def comb2(k: int) -> int:
            return k * (k - 1) // 2
            
        Q_total = 0
        for session in sessions:
            G = session.get_group_num()
            if G <= 0:
                continue
            q, r = divmod(N, G)  # r個が(q+1), G-r個がq
            Q_total += (G - r) * comb2(q) + r * comb2(q + 1)
        lb = (2 * Q_total) / N - (N - 1)
        return max(0.0, lb)


class DistinctPartnersCalculator:
    """各人が同じグループになった「異なる人の数」を集計するクラス"""
    
    @staticmethod
    def calculate_distinct_partners(groups_dict: Dict[int, Groups]) -> Dict[str, int]:
        """各人が同じグループになった「異なる人の数」を集計"""
        # 参加者ID -> 参加者名
        id_to_name: Dict[str, str] = {}
        # 参加者ID -> 同席した相手ID集合
        mates: Dict[str, set[str]] = {}
        
        for _, session_groups in groups_dict.items():
            for group in session_groups:
                ids = []
                for p in group.get_participants():
                    pid = p.get_id().as_str()
                    id_to_name[pid] = p.get_name().as_str()
                    mates.setdefault(pid, set())
                    ids.append(pid)
                # 同一グループ内のペアを記録
                for i in range(len(ids)):
                    for j in range(len(ids)):
                        if i == j:
                            continue
                        mates[ids[i]].add(ids[j])
                        
        # 名前をキーにして人数を出力
        result: Dict[str, int] = {}
        for pid, others in mates.items():
            result[id_to_name.get(pid, pid)] = len(others)
        return result
    
    @staticmethod
    def calculate_partner_statistics(groups_dict: Dict[int, Groups]) -> Dict[str, Dict[str, int]]:
        """各人のパートナー統計を計算（重複含む総数、重複した人の総数、異なる人の数）"""
        # 参加者ID -> 参加者名
        id_to_name: Dict[str, str] = {}
        # 参加者ID -> 同席した相手ID集合（重複なし）
        distinct_mates: Dict[str, set[str]] = {}
        # 参加者ID -> 同席した相手IDリスト（重複あり）
        total_mates: Dict[str, list[str]] = {}
        # 参加者ID -> 重複した相手ID集合
        duplicate_mates: Dict[str, set[str]] = {}
        
        for _, session_groups in groups_dict.items():
            for group in session_groups:
                ids = []
                for p in group.get_participants():
                    pid = p.get_id().as_str()
                    id_to_name[pid] = p.get_name().as_str()
                    distinct_mates.setdefault(pid, set())
                    total_mates.setdefault(pid, [])
                    duplicate_mates.setdefault(pid, set())
                    ids.append(pid)
                
                # 同一グループ内のペアを記録
                for i in range(len(ids)):
                    for j in range(len(ids)):
                        if i == j:
                            continue
                        mate_id = ids[j]
                        distinct_mates[ids[i]].add(mate_id)
                        total_mates[ids[i]].append(mate_id)
        
        # 重複した相手を特定
        for pid, mate_list in total_mates.items():
            mate_counts = {}
            for mate_id in mate_list:
                mate_counts[mate_id] = mate_counts.get(mate_id, 0) + 1
            # 2回以上一緒になった相手を重複として記録
            for mate_id, count in mate_counts.items():
                if count > 1:
                    duplicate_mates[pid].add(mate_id)
        
        # 結果を構築
        result: Dict[str, Dict[str, int]] = {}
        for pid in distinct_mates.keys():
            name = id_to_name.get(pid, pid)
            result[name] = {
                "distinct_partners": len(distinct_mates[pid]),
                "total_partners": len(total_mates[pid]),
                "duplicate_partners": len(duplicate_mates[pid])
            }
        
        return result