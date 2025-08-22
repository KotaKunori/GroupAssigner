from collections import defaultdict
import logging
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from ...domain_layer.services.group_assigner import GroupAssigner
from ...domain_layer.entities.program import Program
from ...domain_layer.first_class_collections.participants import Participants
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.entities.group import Group
from ...domain_layer.entities.participant import PositionType

logger = logging.getLogger(__name__)

class GroupAssignerORTools(GroupAssigner):
    """
    Group assigner using OR-Tools Constraint Programming (CP).
    """
    
    def assign_groups(self, program: Program) -> Dict[int, Groups]:
        """
        OR-Toolsを使用してグループ割り当てを実行
        """
        sessions = program.get_sessions()
        sessions_list = [s for s in sessions]
        
        results: Dict[int, Groups] = {}
        
        for session_index, session in enumerate(sessions):
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
        単一セッションのグループ割り当てを実行
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
            # ラボ情報を数値IDに変換（簡略化）
            lab_names = participant.get_lab()
            if lab_names and len(lab_names) > 0:
                # LaboratoryNameは__iter__を実装しているので、リストとして扱える
                first_lab = list(lab_names)[0] if lab_names else "default"
                labs.append(hash(first_lab) % 10)  # ラボ名をハッシュ化して数値IDに
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
        
        # グローバル制約の適用（Domain Constraint 依存なし）
        # 1) 教員必須（可能な限り）
        for g in range(N_GROUPS):
            faculty_count = sum(
                x[p, 0, g] for p in range(N_PEOPLE)
                if positions[p] == PositionType.FACULTY
            )
            model.Add(faculty_count >= 1)

        # 2) 職位バランス: 過半数抑止（4人の場合は最大2人）
        for g in range(N_GROUPS):
            for pos in PositionType:
                pos_count = sum(
                    x[p, 0, g] for p in range(N_PEOPLE)
                    if positions[p] == pos
                )
                # min/maxベースで上限は ceil(group_size/2)。group_sizeは変数だが上限maxで近似
                model.Add(pos_count <= 2)

        # 3) ラボバランス: 同一ラボは最大2名
        for g in range(N_GROUPS):
            for lab in set(labs):
                lab_count = sum(
                    x[p, 0, g] for p in range(N_PEOPLE)
                    if labs[p] == lab
                )
                model.Add(lab_count <= 2)
        
        # 目的関数の設定
        self._set_objective_function(model, x, y, positions, labs, N_PEOPLE, N_GROUPS)
        
        # ソルバー実行
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30  # 30秒のタイムアウト
        solver.parameters.num_search_workers = 8
        
        status = solver.Solve(model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logger.info(f"Solution found: {status}")
            return self._extract_solution(solver, x, N_PEOPLE, N_GROUPS)
        else:
            logger.warning(f"No solution found: {status}")
            # フォールバック: ランダムな割り当て
            return self._fallback_assignment(session)
    
    # constraints removed
    
    def _set_objective_function(self, model, x, y, positions, labs, N_PEOPLE, N_GROUPS):
        """
        目的関数を設定
        """
        obj_terms = []
        
        # ペア重複の最小化
        for p in range(N_PEOPLE):
            for q in range(p + 1, N_PEOPLE):
                obj_terms.append(y[p, q, 0])  # 単一セッション
        
        # 職位バランスの最適化
        for g in range(N_GROUPS):
            for pos in PositionType:
                pos_count = sum(
                    y[p, q, 0] for p in range(N_PEOPLE) 
                    for q in range(p + 1, N_PEOPLE)
                    if positions[p] == pos and positions[q] == pos
                )
                obj_terms.append(pos_count)
        
        # ラボバランスの最適化
        for g in range(N_GROUPS):
            for lab in set(labs):
                lab_count = sum(
                    y[p, q, 0] for p in range(N_PEOPLE) 
                    for q in range(p + 1, N_PEOPLE)
                    if labs[p] == lab and labs[q] == lab
                )
                obj_terms.append(lab_count)
        
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
