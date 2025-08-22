import logging
from typing import Dict, List, Tuple
from collections import defaultdict

from ortools.sat.python import cp_model

from ...domain_layer.services.group_assigner import GroupAssigner
from ...domain_layer.entities.program import Program
from ...domain_layer.first_class_collections.participants import Participants
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.entities.group import Group
from ...domain_layer.entities.participant import PositionType

logger = logging.getLogger(__name__)

class GroupAssignerORToolsRelaxed(GroupAssigner):
    """
    Relaxed Group assigner using OR-Tools Constraint Programming (CP).
    Constraints are relaxed to ensure feasible solutions.
    """
    
    def assign_groups(self, program: Program) -> Dict[int, Groups]:
        """
        OR-Toolsを使用してグループ割り当てを実行（制約緩和版）
        """
        sessions = program.get_sessions()
        sessions_list = [s for s in sessions]
        
        results: Dict[int, Groups] = {}
        
        for session_index, session in enumerate(sessions_list):
            logger.info(f"Processing session {session_index}")
            
            # セッションごとにグループ割り当てを実行
            session_groups = self._assign_groups_for_session(session)
            
            # Groupsオブジェクトに変換
            group_objs = Groups.empty()
            for group in session_groups:
                ps = Participants.empty()
                for p_index in group:
                    ps = ps.add_participant(session.get_participants().get_participant_by_index(p_index))
                group_objs = group_objs.add_group(Group.create(ps))
            
            results[session_index] = group_objs
        
        return results
    
    def _assign_groups_for_session(self, session) -> List[List[int]]:
        """
        単一セッションのグループ割り当てを実行（制約緩和版）
        """
        participants_fc = session.get_participants()
        N_PEOPLE = participants_fc.length()
        N_SESSIONS = 1  # 単一セッション
        GROUP_SIZE = session.get_max()  # 最大グループサイズ
        N_GROUPS = session.get_group_num()
        
        # 各人の属性を取得
        positions = []
        labs = []
        for i in range(N_PEOPLE):
            participant = participants_fc.get_participant_by_index(i)
            positions.append(participant.get_position())
            # ラボ情報を数値IDに変換
            lab_names = participant.get_lab()
            if lab_names and len(lab_names) > 0:
                first_lab = list(lab_names)[0] if lab_names else "default"
                labs.append(hash(first_lab) % 10)
            else:
                labs.append(0)
        
        # CPモデルを作成
        model = cp_model.CpModel()
        
        # 変数 x[p,s,g] = 1 if person p in session s group g
        x = {}
        for p in range(N_PEOPLE):
            for s in range(N_SESSIONS):
                for g in range(N_GROUPS):
                    x[p, s, g] = model.NewBoolVar(f"x_{p}_{s}_{g}")
        
        # 各人は各セッションで1つのグループに所属
        for p in range(N_PEOPLE):
            for s in range(N_SESSIONS):
                model.Add(sum(x[p, s, g] for g in range(N_GROUPS)) == 1)
        
        # 各グループのサイズ制約
        for s in range(N_SESSIONS):
            for g in range(N_GROUPS):
                min_size = session.get_min()
                max_size = session.get_max()
                model.Add(sum(x[p, s, g] for p in range(N_PEOPLE)) >= min_size)
                model.Add(sum(x[p, s, g] for p in range(N_PEOPLE)) <= max_size)
        
        # ペア変数 y[p,q,s] - 同じグループにいるかどうか
        y = {}
        for p in range(N_PEOPLE):
            for q in range(p + 1, N_PEOPLE):
                for s in range(N_SESSIONS):
                    y[p, q, s] = model.NewBoolVar(f"y_{p}_{q}_{s}")
                    # y[p,q,s] = 1 iff p and q are in the same group in session s
                    for g in range(N_GROUPS):
                        model.Add(y[p, q, s] >= x[p, s, g] + x[q, s, g] - 1)
                    model.Add(y[p, q, s] <= sum(x[p, s, g] for g in range(N_GROUPS)))
                    model.Add(y[p, q, s] <= sum(x[q, s, g] for g in range(N_GROUPS)))
        
        # グローバル制約（緩和版）
        for g in range(N_GROUPS):
            faculty_count = sum(
                x[p, 0, g] for p in range(N_PEOPLE)
                if positions[p] == PositionType.FACULTY
            )
            model.Add(faculty_count >= 1)

        for g in range(N_GROUPS):
            for pos in PositionType:
                pos_count = sum(
                    x[p, 0, g] for p in range(N_PEOPLE)
                    if positions[p] == pos
                )
                model.Add(pos_count <= 3)

        for g in range(N_GROUPS):
            for lab in set(labs):
                lab_count = sum(
                    x[p, 0, g] for p in range(N_PEOPLE)
                    if labs[p] == lab
                )
                model.Add(lab_count <= 3)
        
        # 目的関数の設定（緩和版）
        self._set_relaxed_objective_function(model, x, y, positions, labs, N_PEOPLE, N_GROUPS)
        
        # ソルバー実行
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 120  # タイムアウトを延長
        solver.parameters.num_search_workers = 8
        
        status = solver.Solve(model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logger.info(f"Solution found: {status}")
            return self._extract_solution(solver, x, N_PEOPLE, N_GROUPS)
        else:
            logger.warning(f"No solution found: {status}")
            # フォールバック: シンプルな割り当て
            return self._fallback_assignment(session)
    
    # constraints removed
    
    def _set_relaxed_objective_function(self, model, x, y, positions, labs, N_PEOPLE, N_GROUPS):
        """
        緩和された目的関数を設定
        """
        obj_terms = []
        
        # ペア重複の最小化（最も重要）
        for p in range(N_PEOPLE):
            for q in range(p + 1, N_PEOPLE):
                obj_terms.append(y[p, q, 0])
        
        # 職位バランスのペナルティ（軽減）
        for g in range(N_GROUPS):
            for pos in PositionType:
                pos_count = sum(
                    x[p, 0, g] for p in range(N_PEOPLE) 
                    if positions[p] == pos
                )
                # 理想的な配分からの偏差（より緩和）
                ideal = 1  # 各職位1人ずつが理想的
                deviation = model.NewIntVar(0, 4, f"dev_{pos}_{g}")
                model.Add(deviation >= pos_count - ideal)
                model.Add(deviation >= ideal - pos_count)
                # 重みを軽減
                obj_terms.append(deviation * 0.1)  # 重みを0.1倍に
        
        # ラボバランスのペナルティ（軽減）
        for g in range(N_GROUPS):
            for lab in set(labs):
                lab_count = sum(
                    x[p, 0, g] for p in range(N_PEOPLE) 
                    if labs[p] == lab
                )
                # 上限3を超える場合のペナルティ（軽減）
                excess = model.NewIntVar(0, 4, f"excess_{lab}_{g}")
                model.Add(excess >= lab_count - 3)
                model.Add(excess <= lab_count - 3).OnlyEnforceIf(
                    model.NewBoolVar(f"over_limit_{lab}_{g}")
                )
                # 重みを軽減
                obj_terms.append(excess * 0.1)  # 重みを0.1倍に
        
        model.Minimize(sum(obj_terms))
    
    def _extract_solution(self, solver, x, N_PEOPLE, N_GROUPS) -> List[List[int]]:
        """
        ソルバーの解からグループ割り当てを抽出
        """
        groups = [[] for _ in range(N_GROUPS)]
        
        for p in range(N_PEOPLE):
            for g in range(N_GROUPS):
                if solver.Value(x[p, 0, g]) == 1:
                    groups[g].append(p)
        
        return groups
    
    def _fallback_assignment(self, session) -> List[List[int]]:
        """
        フォールバック: シンプルな割り当て
        """
        participants_fc = session.get_participants()
        N_PEOPLE = participants_fc.length()
        N_GROUPS = session.get_group_num()
        
        # 参加者をインデックスで分割
        indices = list(range(N_PEOPLE))
        group_size = N_PEOPLE // N_GROUPS
        remainder = N_PEOPLE % N_GROUPS
        
        groups = []
        start = 0
        for g in range(N_GROUPS):
            end = start + group_size + (1 if g < remainder else 0)
            groups.append(indices[start:end])
            start = end
        
        return groups
