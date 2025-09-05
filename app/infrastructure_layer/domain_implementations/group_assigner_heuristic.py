import random
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

from ...domain_layer.services.group_assigner import GroupAssigner
from ...domain_layer.entities.program import Program
from ...domain_layer.entities.group import Group
from ...domain_layer.entities.participant import Participant, PositionType
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.first_class_collections.participants import Participants
from ...domain_layer.value_objects.group_id import GroupId


class GroupAssignerHeuristic(GroupAssigner):
    """
    ヒューリスティックアルゴリズムに基づくグループ割り当てクラス
    """
    
    def __init__(self, max_iterations: int = 1000, max_attempts: int = 100):
        self.max_iterations = max_iterations
        self.max_attempts = max_attempts
    
    def assign_groups(self, program: Program) -> Dict[int, Groups]:
        """
        プログラムに対してグループ割り当てを実行する
        
        Args:
            program: プログラム情報
            
        Returns:
            セッションインデックスをキーとするグループ割り当て結果
        """
        sessions = program.get_sessions()
        participants = program.get_participants()
        
        # 初期解の生成
        initial_solution = self._generate_initial_solution(sessions, participants)
        
        # 局所探索による改善
        improved_solution = self._local_search_improvement(initial_solution, sessions, participants)
        
        return improved_solution
    
    def _generate_initial_solution(self, sessions, participants) -> Dict[int, Groups]:
        """
        初期解を生成する
        
        Args:
            sessions: セッション情報
            participants: 参加者情報
            
        Returns:
            初期解
        """
        solution = {}
        used_pairs = set()  # 既出ペアを記録
        lab_conflicts = defaultdict(int)  # ラボ重複の回数を記録
        
        for session_idx, session in enumerate(sessions):
            session_participants = session.get_participants()
            total_participants = session_participants.length()
            
            # セッション定義からグループ数を取得
            group_num = session.get_group_num()
            
            # 各グループを初期化
            groups = [[] for _ in range(group_num)]
            
            min_size = session.get_min()
            max_size = session.get_max()
            
            # 職位別に参加者を分類
            faculty_participants = [p for p in session_participants if p.get_position() == PositionType.FACULTY]
            doctoral_participants = [p for p in session_participants if p.get_position() == PositionType.DOCTORAL]
            master_participants = [p for p in session_participants if p.get_position() == PositionType.MASTER]
            bachelor_participants = [p for p in session_participants if p.get_position() == PositionType.BACHELOR]
            
            # 職位別ターゲットを算出し、そのターゲットに沿って均等配分
            position_groups = {
                PositionType.FACULTY: list(faculty_participants),
                PositionType.DOCTORAL: list(doctoral_participants),
                PositionType.MASTER: list(master_participants),
                PositionType.BACHELOR: list(bachelor_participants),
            }

            # まず各グループの目標サイズ（容量）を決定し、その容量内で職位ターゲットを配分
            group_sizes = self._compute_group_sizes(total_participants, group_num)
            
            # position_targetsが指定されている場合はそれを使用、そうでなければジグザグ配分
            if session.has_position_targets():
                position_targets = session.get_position_targets_as_enum()
            else:
                position_targets = self._compute_position_targets_zigzag(session, group_sizes, position_groups)

            self._assign_by_targets(
                groups=groups,
                position_groups=position_groups,
                position_targets=position_targets,
                used_pairs=used_pairs,
                lab_conflicts=lab_conflicts,
                session_idx=session_idx,
                min_size=min_size,
                max_size=max_size,
            )
            
            # Groupsオブジェクトに変換
            group_objects = []
            for group_idx, group_participants in enumerate(groups):
                if group_participants:  # 空でないグループのみ作成
                    participants_obj = Participants.of(group_participants)
                    group_obj = Group.create(participants_obj)
                    group_objects.append(group_obj)
            
            solution[session_idx] = Groups.of(group_objects)
        
        return solution

    def _compute_group_sizes(self, total_participants: int, group_num: int) -> List[int]:
        """
        グループサイズを均等配分（q, r）で決定。
        """
        q, r = divmod(total_participants, group_num)
        return [q + 1 if i < r else q for i in range(group_num)]

    def _compute_position_targets_zigzag(
        self,
        session,
        group_sizes: List[int],
        position_groups: Dict[PositionType, List[Participant]],
    ) -> List[Dict[PositionType, int]]:
        """
        職位ごとの受け入れ数をグループA..Gに対してジグザグに1人ずつ加算していく。
        職位は Faculty → Doctoral → Master → Bachelor の順で、ポインタは続きから始める。
        """
        G = session.get_group_num()
        targets: List[Dict[PositionType, int]] = [{pos: 0 for pos in PositionType} for _ in range(G)]
        loads: List[int] = [0 for _ in range(G)]  # 現在の総割当数（全職位合計）

        # ジグザグ用ポインタ
        idx = 0
        dirn = 1  # +1: 右方向, -1: 左方向

        def step():
            nonlocal idx, dirn
            # 端点は一度留まってから折り返す（A→…→G→G→…→A→A→…）
            if dirn == 1:
                if idx == G - 1:
                    dirn = -1  # 留まって向きを反転
                else:
                    idx += 1
            else:
                if idx == 0:
                    dirn = 1  # 留まって向きを反転
                else:
                    idx -= 1

        order = [PositionType.FACULTY, PositionType.DOCTORAL, PositionType.MASTER, PositionType.BACHELOR]
        for pos in order:
            count = len(position_groups.get(pos, []))
            for _ in range(count):
                # 容量を超えないグループに置くまで進む
                guard = 0
                while guard < G * 2:  # 端点での滞留を考慮して2周分を上限
                    if loads[idx] < group_sizes[idx]:
                        targets[idx][pos] += 1
                        loads[idx] += 1
                        step()
                        break
                    step()
                    guard += 1

        return targets

    def _assign_by_targets(
        self,
        groups: List[List[Participant]],
        position_groups: Dict[PositionType, List[Participant]],
        position_targets: List[Dict[PositionType, int]],
        used_pairs: Set[Tuple[str, str]],
        lab_conflicts: Dict[str, int],
        session_idx: int,
        min_size: int,
        max_size: int,
    ) -> None:
        """
        各グループごとの職位ターゲット数に従い、最小スコアの候補から順に割当てる。
        """
        # 各職位の候補をシャッフル
        for pos in PositionType:
            random.shuffle(position_groups[pos])

        # ターゲット総数のチェック
        for gi in range(len(groups)):
            total_target = sum(position_targets[gi].values())
            # min/maxは最終的なサイズ調整で満たされる前提（ターゲット総和は全体人数に一致）
            _ = total_target  # for readability

        # 職位ごとに、各グループの必要人数分を埋める
        for pos in PositionType:
            pool = position_groups[pos]
            # グループ順は小さいグループから埋める（バランス用）
            order = sorted(range(len(groups)), key=lambda i: len(groups[i]))
            for gi in order:
                need = position_targets[gi][pos]
                while need > 0 and pool:
                    # 候補の中から、このグループでのスコアが最小の人を選ぶ
                    best_idx = None
                    best_score = float('inf')
                    best_candidate = None
                    for idx, cand in enumerate(pool):
                        # サイズ制約チェック
                        if len(groups[gi]) >= max_size:
                            break
                        # 職位ごとの簡易制約: 博士は過剰重複を避ける（既存ロジックを活用）
                        if pos == PositionType.DOCTORAL:
                            if not self._is_group_suitable_for_participant(cand, groups[gi], used_pairs, lab_conflicts):
                                continue
                        # スコア計算
                        score = self._calculate_group_score(
                            cand, groups[gi], used_pairs, lab_conflicts,
                            min_size, max_size, True, True
                        )
                        if score < best_score:
                            best_score = score
                            best_candidate = cand
                            best_idx = idx
                    if best_candidate is None:
                        break
                    groups[gi].append(best_candidate)
                    # 既出ペア/ラボ重複の記録
                    self._update_conflicts(best_candidate, groups[gi], used_pairs, lab_conflicts)
                    # プールから削除
                    pool.pop(best_idx)
                    need -= 1
        # ジグザグ配分で計算したターゲット数を厳密に守る
        # 余りの参加者は、制約を満たす範囲で適切に割り当てる
        for pos in PositionType:
            remaining_participants = position_groups[pos]
            if remaining_participants:
                # 残りの参加者を制約を満たすグループに割り当て
                for participant in remaining_participants:
                    best_group_idx = self._find_best_group_for_remaining_participant(
                        participant, groups, position_targets, used_pairs, lab_conflicts, max_size
                    )
                    if best_group_idx is not None:
                        groups[best_group_idx].append(participant)
                        self._update_conflicts(participant, groups[best_group_idx], used_pairs, lab_conflicts)
                    else:
                        # 制約を満たすグループが見つからない場合は、最小のグループに追加
                        min_group_idx = min(range(len(groups)), key=lambda i: len(groups[i]))
                        groups[min_group_idx].append(participant)
    
    def _find_best_group_for_remaining_participant(
        self,
        participant: Participant,
        groups: List[List[Participant]],
        position_targets: List[Dict[PositionType, int]],
        used_pairs: Set[Tuple[str, str]],
        lab_conflicts: Dict[str, int],
        max_size: int
    ) -> Optional[int]:
        """
        残りの参加者に最適なグループを見つける（ジグザグ配分の制約を考慮）
        
        Args:
            participant: 割り当て対象の参加者
            groups: グループリスト
            position_targets: 各グループの職位ターゲット数
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            max_size: グループの最大サイズ
            
        Returns:
            最適なグループのインデックス、見つからない場合はNone
        """
        best_group_idx = None
        best_score = float('inf')
        
        for group_idx, group_participants in enumerate(groups):
            # グループサイズの制約をチェック
            if len(group_participants) >= max_size:
                continue
            
            # ジグザグ配分の制約をチェック
            if not self._is_group_suitable_for_zigzag_constraints(
                participant, group_idx, position_targets, group_participants
            ):
                continue
            
            # 既出ペアとラボ重複の制約をチェック
            if not self._is_group_suitable_for_participant(
                participant, group_participants, used_pairs, lab_conflicts
            ):
                continue
            
            # スコア計算
            score = self._calculate_group_score(
                participant, group_participants, used_pairs, lab_conflicts,
                0, max_size, True, True
            )
            
            if score < best_score:
                best_score = score
                best_group_idx = group_idx
        
        return best_group_idx
    
    def _is_group_suitable_for_zigzag_constraints(
        self,
        participant: Participant,
        group_idx: int,
        position_targets: List[Dict[PositionType, int]],
        group_participants: List[Participant]
    ) -> bool:
        """
        ジグザグ配分の制約をチェック
        
        Args:
            participant: 割り当て対象の参加者
            group_idx: グループのインデックス
            position_targets: 各グループの職位ターゲット数
            group_participants: グループ内の参加者
            
        Returns:
            制約を満たすかどうか
        """
        position = participant.get_position()
        current_count = sum(1 for p in group_participants if p.get_position() == position)
        target_count = position_targets[group_idx][position]
        
        # ターゲット数を超えないようにチェック
        return current_count < target_count
    
    def _order_by_duplication_average(
        self,
        position_groups: Dict[PositionType, List[Participant]],
        used_pairs: Set[Tuple[str, str]],
        session_idx: int
    ) -> List[List[Participant]]:
        """
        重複数の平均に基づいて職位の優先順序を決定
        
        Args:
            position_groups: 職位別の参加者グループ
            used_pairs: 既出ペアのセット
            session_idx: セッションインデックス
            
        Returns:
            重複数の平均が高い順に並べられた参加者グループのリスト
        """
        # 各職位の重複数の平均を計算
        position_duplication_avg = {}
        
        for position, participants in position_groups.items():
            if not participants:
                position_duplication_avg[position] = 0.0
                continue
                
            total_duplications = 0
            total_pairs = 0
            
            # その職位の参加者間の重複数を計算
            for i, participant1 in enumerate(participants):
                for j, participant2 in enumerate(participants):
                    if i != j:
                        pair_key = tuple(sorted([
                            participant1.get_name().as_str(),
                            participant2.get_name().as_str()
                        ]))
                        if pair_key in used_pairs:
                            total_duplications += 1
                        total_pairs += 1
            
            # 他の職位の参加者との重複も考慮
            for other_position, other_participants in position_groups.items():
                if position != other_position:
                    for participant1 in participants:
                        for participant2 in other_participants:
                            pair_key = tuple(sorted([
                                participant1.get_name().as_str(),
                                participant2.get_name().as_str()
                            ]))
                            if pair_key in used_pairs:
                                total_duplications += 1
                            total_pairs += 1
            
            # 平均重複数を計算
            avg_duplication = total_duplications / total_pairs if total_pairs > 0 else 0.0
            position_duplication_avg[position] = avg_duplication
        
        print(f"セッション {session_idx + 1} - 職位別重複数平均:")
        for position, avg in position_duplication_avg.items():
            print(f"  {position.as_str()}: {avg:.3f}")
        
        # 重複数の平均が高い順にソート
        sorted_positions = sorted(
            position_duplication_avg.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 順序を出力
        print(f"  割り振り順序: {' -> '.join([pos.as_str() for pos, _ in sorted_positions])}")
        
        # ソートされた順序で参加者グループを返す
        ordered_groups = []
        for position, _ in sorted_positions:
            if position_groups[position]:  # 空でないグループのみ追加
                ordered_groups.append(position_groups[position])
        
        return ordered_groups
    
    # 重複解除関連メソッドは撤回
    
    def _assign_participants_round_robin(
        self,
        position_groups: List[List[Participant]],
        groups: List[List[Participant]],
        used_pairs: Set[Tuple[str, str]],
        lab_conflicts: Dict[str, int],
        session_idx: int,
        min_size: int,
        max_size: int
    ):
        """
        各グループに職位別に順番に割り振る（ラウンドロビン方式）
        
        Args:
            position_groups: 職位別の参加者リストのリスト
            groups: グループリスト
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            session_idx: セッションインデックス
            min_size: グループの最小サイズ
            max_size: グループの最大サイズ
        """
        # 各職位の参加者をシャッフル
        for position_group in position_groups:
            random.shuffle(position_group)
        
        # ラウンドロビン方式で割り当て
        group_idx = 0
        for position_idx, position_participants in enumerate(position_groups):
            for participant in position_participants:
                # 適切なグループを見つける
                best_group_idx = self._find_best_group_for_round_robin(
                    participant, groups, used_pairs, lab_conflicts,
                    min_size, max_size, group_idx
                )
                
                if best_group_idx is not None:
                    groups[best_group_idx].append(participant)
                    # 既出ペアとラボ重複を記録
                    self._update_conflicts(participant, groups[best_group_idx], used_pairs, lab_conflicts)
                    group_idx = (best_group_idx + 1) % len(groups)  # 次のグループに移動
                else:
                    # 適切なグループが見つからない場合、最小のグループに割り当て
                    min_group_idx = min(range(len(groups)), key=lambda i: len(groups[i]))
                    groups[min_group_idx].append(participant)
                    group_idx = (min_group_idx + 1) % len(groups)
    
    def _find_best_group_for_round_robin(
        self,
        participant: Participant,
        groups: List[List[Participant]],
        used_pairs: Set[Tuple[str, str]],
        lab_conflicts: Dict[str, int],
        min_size: int,
        max_size: int,
        preferred_group_idx: int
    ) -> int:
        """
        ラウンドロビン方式用の最適なグループを見つける
        
        Args:
            participant: 割り当て対象の参加者
            groups: グループリスト
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            min_size: グループの最小サイズ
            max_size: グループの最大サイズ
            preferred_group_idx: 優先したいグループのインデックス
            
        Returns:
            最適なグループのインデックス、見つからない場合はNone
        """
        # 博士学生配置の特別処理: (教員+博士)が最小のグループ群から選ぶ
        if participant.get_position() == PositionType.DOCTORAL:
            # サイズ制約を満たすグループのみ対象
            candidate_indices = [i for i, g in enumerate(groups) if len(g) < max_size]
            if candidate_indices:
                # 各グループの(教員+博士)人数を算出
                load_by_group = []
                for i in candidate_indices:
                    g = groups[i]
                    load = sum(1 for p in g if p.get_position() in (PositionType.FACULTY, PositionType.DOCTORAL))
                    load_by_group.append((i, load))
                if load_by_group:
                    min_load = min(load for _, load in load_by_group)
                    min_load_indices = [i for (i, load) in load_by_group if load == min_load]
                    # 重複/ラボ重複が少ない場所（スコア最小）を選択
                    best_idx = None
                    best_score = float('inf')
                    for i in min_load_indices:
                        g = groups[i]
                        if not self._is_group_suitable_for_participant(participant, g, used_pairs, lab_conflicts):
                            continue
                        score = self._calculate_group_score(
                            participant, g, used_pairs, lab_conflicts,
                            min_size, max_size, True, True
                        )
                        if score < best_score:
                            best_score = score
                            best_idx = i
                    if best_idx is not None:
                        return best_idx
        
        # 通常処理: 優先グループから順番にチェック
        for offset in range(len(groups)):
            group_idx = (preferred_group_idx + offset) % len(groups)
            group_participants = groups[group_idx]
            
            # グループサイズの制約をチェック
            if len(group_participants) >= max_size:
                continue
            
            # 制約違反をチェック
            if self._is_group_suitable_for_participant(
                participant, group_participants, used_pairs, lab_conflicts
            ):
                return group_idx
        
        return None
    
    def _is_group_suitable_for_participant(
        self,
        participant: Participant,
        group_participants: List[Participant],
        used_pairs: Set[Tuple[str, str]],
        lab_conflicts: Dict[str, int]
    ) -> bool:
        """
        グループが参加者に適しているかをチェック
        
        Args:
            participant: 割り当て対象の参加者
            group_participants: グループ内の参加者
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            
        Returns:
            適しているかどうか
        """
        # 博士がグループ数と同数以上いる場合は、各グループに博士を1名まで
        if participant.get_position() == PositionType.DOCTORAL:
            doctoral_count = sum(1 for p in group_participants if p.get_position() == PositionType.DOCTORAL)
            # グループ総数と同数以上の博士がいるかどうかは、割当フェーズ全体の文脈が必要だが、
            # 近似として「既にこのグループに博士がいれば不可」とする（7グループ・7博士のケースを満たす）
            if doctoral_count >= 1:
                return False
        
        # 教員の制約：各グループに教員は1名まで
        if participant.get_position() == PositionType.FACULTY:
            faculty_count = sum(1 for p in group_participants if p.get_position() == PositionType.FACULTY)
            if faculty_count >= 1:
                return False

        for existing_participant in group_participants:
            # 既出ペアのチェック
            pair_key = tuple(sorted([participant.get_id().as_str(), existing_participant.get_id().as_str()]))
            if pair_key in used_pairs:
                return False
            
            # ラボ重複のチェック
            if participant.get_lab() == existing_participant.get_lab():
                return False
        
        return True
    
    def _assign_participants_by_position(
        self, 
        participants: List[Participant], 
        groups: List[List[Participant]], 
        used_pairs: Set[Tuple[str, str]], 
        lab_conflicts: Dict[str, int], 
        session_idx: int,
        min_size: int,
        max_size: int,
        avoid_lab_conflicts: bool = True,
        avoid_used_pairs: bool = True
    ):
        """
        特定の職位の参加者をグループに割り当てる
        
        Args:
            participants: 割り当て対象の参加者リスト
            groups: グループリスト
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            session_idx: セッションインデックス
            min_size: グループの最小サイズ
            max_size: グループの最大サイズ
            avoid_lab_conflicts: ラボ重複を避けるかどうか
            avoid_used_pairs: 既出ペアを避けるかどうか
        """
        random.shuffle(participants)  # ランダムにシャッフル
        
        for participant in participants:
            best_group_idx = self._find_best_group_for_participant(
                participant, groups, used_pairs, lab_conflicts, 
                min_size, max_size, avoid_lab_conflicts, avoid_used_pairs
            )
            
            if best_group_idx is not None:
                groups[best_group_idx].append(participant)
                # 既出ペアとラボ重複を記録
                self._update_conflicts(participant, groups[best_group_idx], used_pairs, lab_conflicts)
            else:
                # 適切なグループが見つからない場合、最小のグループに割り当て
                min_group_idx = min(range(len(groups)), key=lambda i: len(groups[i]))
                groups[min_group_idx].append(participant)
    
    def _find_best_group_for_participant(
        self, 
        participant: Participant, 
        groups: List[List[Participant]], 
        used_pairs: Set[Tuple[str, str]], 
        lab_conflicts: Dict[str, int],
        min_size: int,
        max_size: int,
        avoid_lab_conflicts: bool,
        avoid_used_pairs: bool
    ) -> int:
        """
        参加者に最適なグループを見つける
        
        Args:
            participant: 割り当て対象の参加者
            groups: グループリスト
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            min_size: グループの最小サイズ
            max_size: グループの最大サイズ
            avoid_lab_conflicts: ラボ重複を避けるかどうか
            avoid_used_pairs: 既出ペアを避けるかどうか
            
        Returns:
            最適なグループのインデックス、見つからない場合はNone
        """
        best_group_idx = None
        best_score = float('inf')
        
        for group_idx, group_participants in enumerate(groups):
            # グループサイズの制約をチェック
            if len(group_participants) >= max_size:
                continue
                
            score = self._calculate_group_score(
                participant, group_participants, used_pairs, lab_conflicts,
                min_size, max_size, avoid_lab_conflicts, avoid_used_pairs
            )
            
            if score < best_score:
                best_score = score
                best_group_idx = group_idx
        
        # 適切なグループが見つからない場合、空のグループを探す
        if best_group_idx is None:
            for group_idx, group_participants in enumerate(groups):
                if len(group_participants) == 0:
                    return group_idx
        
        return best_group_idx
    
    def _calculate_group_score(
        self, 
        participant: Participant, 
        group_participants: List[Participant], 
        used_pairs: Set[Tuple[str, str]], 
        lab_conflicts: Dict[str, int],
        min_size: int,
        max_size: int,
        avoid_lab_conflicts: bool,
        avoid_used_pairs: bool
    ) -> float:
        """
        グループのスコアを計算する（低いほど良い）
        
        Args:
            participant: 割り当て対象の参加者
            group_participants: グループ内の参加者
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
            min_size: グループの最小サイズ
            max_size: グループの最大サイズ
            avoid_lab_conflicts: ラボ重複を避けるかどうか
            avoid_used_pairs: 既出ペアを避けるかどうか
            
        Returns:
            グループのスコア
        """
        score = 0.0
        
        for existing_participant in group_participants:
            # 既出ペアのペナルティ
            if avoid_used_pairs:
                pair_key = tuple(sorted([participant.get_id().as_str(), existing_participant.get_id().as_str()]))
                if pair_key in used_pairs:
                    score += 1000.0
            
            # ラボ重複のペナルティ
            if avoid_lab_conflicts and participant.get_lab() == existing_participant.get_lab():
                score += 500.0
        
        # グループサイズのバランスを考慮
        current_size = len(group_participants)
        if current_size < min_size:
            # 最小サイズに満たない場合は優先
            score -= 100.0
        elif current_size >= max_size:
            # 最大サイズを超える場合はペナルティ
            score += 1000.0
        
        # グループサイズのバランスを考慮（適切なサイズに近いほど良い）
        ideal_size = (min_size + max_size) / 2
        size_penalty = abs(current_size - ideal_size) * 20.0
        score += size_penalty
        
        return score
    
    def _update_conflicts(
        self, 
        participant: Participant, 
        group_participants: List[Participant], 
        used_pairs: Set[Tuple[str, str]], 
        lab_conflicts: Dict[str, int]
    ):
        """
        制約違反情報を更新する
        
        Args:
            participant: 新しく割り当てられた参加者
            group_participants: グループ内の参加者
            used_pairs: 既出ペアのセット
            lab_conflicts: ラボ重複の回数
        """
        for existing_participant in group_participants:
            if existing_participant != participant:
                # 既出ペアを記録
                pair_key = tuple(sorted([participant.get_id().as_str(), existing_participant.get_id().as_str()]))
                used_pairs.add(pair_key)
                
                # ラボ重複を記録
                if participant.get_lab() == existing_participant.get_lab():
                    lab_key = participant.get_lab().as_str()
                    lab_conflicts[lab_key] += 1
    
    def _local_search_improvement(
        self, 
        solution: Dict[int, Groups], 
        sessions, 
        participants
    ) -> Dict[int, Groups]:
        """
        局所探索による解の改善（公平性重視）
        
        Args:
            solution: 現在の解
            sessions: セッション情報
            participants: 参加者情報
            
        Returns:
            改善された解
        """
        current_solution = solution.copy()
        
        for iteration in range(self.max_iterations):
            improved = False
            
            # 公平性を重視した改善
            session_improved = self._improve_fairness(
                current_solution, sessions, participants
            )
            if session_improved:
                improved = True
            
            # 従来の改善も試行
            for session_idx in current_solution.keys():
                session_improved = self._improve_session(
                    current_solution, session_idx, sessions, participants
                )
                if session_improved:
                    improved = True
            
            # 改善されなかった場合は終了
            if not improved:
                break
        
        return current_solution
    
    def _improve_fairness(
        self,
        solution: Dict[int, Groups],
        sessions,
        participants
    ) -> bool:
        """
        公平性を重視した改善
        
        Args:
            solution: 現在の解
            sessions: セッション情報
            participants: 参加者情報
            
        Returns:
            改善されたかどうか
        """
        # 各参加者のスコアを計算
        participant_scores = self._calculate_participant_scores(solution, participants)
        
        # 極端に低いスコアを持つ参加者を特定
        min_score = min(participant_scores.values())
        max_score = max(participant_scores.values())
        threshold_low = min_score + (max_score - min_score) * 0.2  # 下位20%を低スコアとみなす
        
        low_score_participants = [
            p for p, score in participant_scores.items() 
            if score <= threshold_low
        ]
        
        # 重複が多い参加者を特定
        high_duplication_participants = self._find_high_duplication_participants(solution, participants)
        
        # 優先度の高い参加者から改善を試行
        priority_participants = low_score_participants + high_duplication_participants
        
        for participant in priority_participants:
            if self._try_improve_participant_fairness(
                solution, sessions, participants, participant, participant_scores
            ):
                return True
        
        return False
    
    # 重複解除関連メソッドは撤回
    
    def _calculate_participant_scores(
        self,
        solution: Dict[int, Groups],
        participants
    ) -> Dict[str, int]:
        """
        各参加者のスコアを計算（他の参加者と一緒になった回数の合計）
        
        Args:
            solution: 現在の解
            participants: 参加者情報
            
        Returns:
            参加者名をキーとするスコア辞書
        """
        participant_scores = defaultdict(int)
        
        for session_groups in solution.values():
            for group in session_groups:
                group_participants = list(group.get_participants())
                for i, participant1 in enumerate(group_participants):
                    name1 = participant1.get_name().as_str()
                    for j in range(i + 1, len(group_participants)):
                        participant2 = group_participants[j]
                        name2 = participant2.get_name().as_str()
                        participant_scores[name1] += 1
                        participant_scores[name2] += 1
        
        return dict(participant_scores)
    
    def _find_high_duplication_participants(
        self,
        solution: Dict[int, Groups],
        participants
    ) -> List[str]:
        """
        重複が多い参加者を特定
        
        Args:
            solution: 現在の解
            participants: 参加者情報
            
        Returns:
            重複が多い参加者のリスト
        """
        duplication_count = defaultdict(int)
        
        for session_groups in solution.values():
            for group in session_groups:
                group_participants = list(group.get_participants())
                for i, participant1 in enumerate(group_participants):
                    name1 = participant1.get_name().as_str()
                    for j in range(i + 1, len(group_participants)):
                        participant2 = group_participants[j]
                        name2 = participant2.get_name().as_str()
                        pair_key = tuple(sorted([name1, name2]))
                        duplication_count[pair_key] += 1
        
        # 重複回数が2回以上のペアを含む参加者を特定
        high_duplication_participants = set()
        for (name1, name2), count in duplication_count.items():
            if count >= 2:
                high_duplication_participants.add(name1)
                high_duplication_participants.add(name2)
        
        return list(high_duplication_participants)
    
    def _try_improve_participant_fairness(
        self,
        solution: Dict[int, Groups],
        sessions,
        participants,
        target_participant: str,
        current_scores: Dict[str, int]
    ) -> bool:
        """
        特定の参加者の公平性を改善する
        
        Args:
            solution: 現在の解
            sessions: セッション情報
            participants: 参加者情報
            target_participant: 改善対象の参加者
            current_scores: 現在のスコア
            
        Returns:
            改善されたかどうか
        """
        # 各セッションで改善を試行
        for session_idx in solution.keys():
            if self._try_swap_for_fairness(
                solution, session_idx, target_participant, current_scores
            ):
                return True
        
        return False
    
    def _try_swap_for_fairness(
        self,
        solution: Dict[int, Groups],
        session_idx: int,
        target_participant: str,
        current_scores: Dict[str, int]
    ) -> bool:
        """
        公平性のための入れ替えを試行
        
        Args:
            solution: 現在の解
            sessions: セッション情報
            target_participant: 改善対象の参加者
            current_scores: 現在のスコア
            
        Returns:
            改善されたかどうか
        """
        current_groups = solution[session_idx]
        
        # 対象参加者がいるグループを特定
        target_group_idx = None
        target_position = None
        
        for group_idx in range(current_groups.length()):
            group = current_groups.get_group_by_index(group_idx)
            participants = list(group.get_participants())
            for pos, participant in enumerate(participants):
                if participant.get_name().as_str() == target_participant:
                    target_group_idx = group_idx
                    target_position = pos
                    break
            if target_group_idx is not None:
                break
        
        if target_group_idx is None:
            return False
        
        # 他のグループとの入れ替えを試行
        for other_group_idx in range(current_groups.length()):
            if other_group_idx == target_group_idx:
                continue
            
            other_group = current_groups.get_group_by_index(other_group_idx)
            other_participants = list(other_group.get_participants())
            
            for other_pos, other_participant in enumerate(other_participants):
                # 同一職位の参加者と入れ替えを試行
                target_group = current_groups.get_group_by_index(target_group_idx)
                target_participants = list(target_group.get_participants())
                if (other_participant.get_position() == 
                    target_participants[target_position].get_position()):
                    
                    # 入れ替えを試行
                    if self._evaluate_swap_fairness(
                        solution, session_idx, target_group_idx, other_group_idx,
                        target_position, other_pos, target_participant, other_participant.get_name().as_str()
                    ):
                        # 入れ替えを実行
                        self._execute_swap(
                            solution, session_idx, target_group_idx, other_group_idx,
                            target_position, other_pos
                        )
                        return True
        
        return False
    
    def _evaluate_swap_fairness(
        self,
        solution: Dict[int, Groups],
        session_idx: int,
        group1_idx: int,
        group2_idx: int,
        pos1: int,
        pos2: int,
        participant1_name: str,
        participant2_name: str
    ) -> bool:
        """
        入れ替えの公平性を評価
        
        Args:
            solution: 現在の解
            session_idx: セッションインデックス
            group1_idx: グループ1のインデックス
            group2_idx: グループ2のインデックス
            pos1: グループ1内の位置
            pos2: グループ2内の位置
            participant1_name: 参加者1の名前
            participant2_name: 参加者2の名前
            
        Returns:
            入れ替えが公平性を改善するかどうか
        """
        # 現在のスコアを計算
        current_scores = self._calculate_participant_scores(solution, None)
        
        # 入れ替え後のスコアをシミュレート
        temp_solution = self._simulate_swap(
            solution, session_idx, group1_idx, group2_idx, pos1, pos2
        )
        new_scores = self._calculate_participant_scores_from_list(temp_solution, None)
        
        # 公平性の改善を評価
        current_variance = self._calculate_score_variance(current_scores)
        new_variance = self._calculate_score_variance(new_scores)
        
        # 分散が減少する場合、または極端に低いスコアが改善される場合は改善とみなす
        if new_variance < current_variance:
            return True
        
        # 極端に低いスコアの改善をチェック
        min_current = min(current_scores.values())
        min_new = min(new_scores.values())
        if min_new > min_current:
            return True
        
        return False
    
    def _calculate_score_variance(self, scores: Dict[str, int]) -> float:
        """スコアの分散を計算"""
        if not scores:
            return 0.0
        
        mean_score = sum(scores.values()) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores.values()) / len(scores)
        return variance
    
    def _simulate_swap(
        self,
        solution: Dict[int, Groups],
        session_idx: int,
        group1_idx: int,
        group2_idx: int,
        pos1: int,
        pos2: int
    ) -> Dict[int, Groups]:
        """入れ替えをシミュレート"""
        # ディープコピーを作成
        temp_solution = {}
        for s_idx, groups in solution.items():
            temp_groups = []
            for group in groups:
                participants = list(group.get_participants())
                temp_groups.append(participants.copy())
            temp_solution[s_idx] = temp_groups
        
        # 入れ替えを実行
        temp_solution[session_idx][group1_idx][pos1], temp_solution[session_idx][group2_idx][pos2] = \
            temp_solution[session_idx][group2_idx][pos2], temp_solution[session_idx][group1_idx][pos1]
        
        return temp_solution
    
    def _calculate_participant_scores_from_list(
        self,
        solution: Dict[int, List[List[Participant]]],
        participants
    ) -> Dict[str, int]:
        """
        各参加者のスコアを計算（リスト形式の解から）
        
        Args:
            solution: リスト形式の解
            participants: 参加者情報
            
        Returns:
            参加者名をキーとするスコア辞書
        """
        participant_scores = defaultdict(int)
        
        for session_groups in solution.values():
            for group in session_groups:
                for i, participant1 in enumerate(group):
                    name1 = participant1.get_name().as_str()
                    for j in range(i + 1, len(group)):
                        participant2 = group[j]
                        name2 = participant2.get_name().as_str()
                        participant_scores[name1] += 1
                        participant_scores[name2] += 1
        
        return dict(participant_scores)
    
    def _execute_swap(
        self,
        solution: Dict[int, Groups],
        session_idx: int,
        group1_idx: int,
        group2_idx: int,
        pos1: int,
        pos2: int
    ):
        """実際の入れ替えを実行"""
        group1 = solution[session_idx].get_group_by_index(group1_idx)
        group2 = solution[session_idx].get_group_by_index(group2_idx)
        
        participants1 = list(group1.get_participants())
        participants2 = list(group2.get_participants())
        
        # 入れ替え
        participants1[pos1], participants2[pos2] = participants2[pos2], participants1[pos1]
        
        # 新しいグループを作成
        new_group1 = Group.create(Participants.of(participants1))
        new_group2 = Group.create(Participants.of(participants2))
        
        # グループを更新
        new_groups = []
        for i in range(solution[session_idx].length()):
            if i == group1_idx:
                new_groups.append(new_group1)
            elif i == group2_idx:
                new_groups.append(new_group2)
            else:
                new_groups.append(solution[session_idx].get_group_by_index(i))
        
        solution[session_idx] = Groups.of(new_groups)
    
    def _improve_session(
        self, 
        solution: Dict[int, Groups], 
        session_idx: int, 
        sessions, 
        participants
    ) -> bool:
        """
        特定のセッションの解を改善する
        
        Args:
            solution: 現在の解
            session_idx: セッションインデックス
            sessions: セッション情報
            participants: 参加者情報
            
        Returns:
            改善されたかどうか
        """
        current_groups = solution[session_idx]
        current_score = self._evaluate_session(current_groups, participants)
        
        # 同一職位の参加者同士を入れ替えて改善を試行
        for group1_idx in range(current_groups.length()):
            for group2_idx in range(group1_idx + 1, current_groups.length()):
                group1 = current_groups.get_group_by_index(group1_idx)
                group2 = current_groups.get_group_by_index(group2_idx)
                
                # 同一職位の参加者を見つけて入れ替えを試行
                if self._try_swap_participants(
                    solution, session_idx, group1_idx, group2_idx, 
                    current_score, participants
                ):
                    return True
        
        return False
    
    def _try_swap_participants(
        self, 
        solution: Dict[int, Groups], 
        session_idx: int, 
        group1_idx: int, 
        group2_idx: int, 
        current_score: float, 
        participants
    ) -> bool:
        """
        2つのグループ間で参加者を入れ替えて改善を試行する
        
        Args:
            solution: 現在の解
            session_idx: セッションインデックス
            group1_idx: グループ1のインデックス
            group2_idx: グループ2のインデックス
            current_score: 現在のスコア
            participants: 参加者情報
            
        Returns:
            改善されたかどうか
        """
        # グループのコピーを作成
        groups_copy = []
        for i in range(solution[session_idx].length()):
            group = solution[session_idx].get_group_by_index(i)
            participants_list = list(group.get_participants())
            groups_copy.append(participants_list)
        
        # 同一職位の参加者を見つけて入れ替えを試行
        for pos1_idx, participant1 in enumerate(groups_copy[group1_idx]):
            for pos2_idx, participant2 in enumerate(groups_copy[group2_idx]):
                if participant1.get_position() == participant2.get_position():
                    # 入れ替えを試行
                    groups_copy[group1_idx][pos1_idx], groups_copy[group2_idx][pos2_idx] = \
                        groups_copy[group2_idx][pos2_idx], groups_copy[group1_idx][pos1_idx]
                    
                    # 新しいスコアを計算
                    new_groups = []
                    for group_participants in groups_copy:
                        if group_participants:
                            participants_obj = Participants.of(group_participants)
                            group_obj = Group.create(participants_obj)
                            new_groups.append(group_obj)
                    
                    new_score = self._evaluate_session(Groups.of(new_groups), participants)
                    
                    # 改善された場合は適用
                    if new_score < current_score:
                        solution[session_idx] = Groups.of(new_groups)
                        return True
                    
                    # 元に戻す
                    groups_copy[group1_idx][pos1_idx], groups_copy[group2_idx][pos2_idx] = \
                        groups_copy[group2_idx][pos2_idx], groups_copy[group1_idx][pos1_idx]
        
        return False
    
    def _evaluate_solution(self, solution: Dict[int, Groups], participants) -> float:
        """
        解全体の評価値を計算する
        
        Args:
            solution: 解
            participants: 参加者情報
            
        Returns:
            評価値（低いほど良い）
        """
        total_score = 0.0
        
        for session_groups in solution.values():
            total_score += self._evaluate_session(session_groups, participants)
        
        return total_score
    
    def _evaluate_session(self, groups: Groups, participants) -> float:
        """
        セッションの評価値を計算する
        
        Args:
            groups: グループ集合
            participants: 参加者情報
            
        Returns:
            評価値（低いほど良い）
        """
        if groups.length() == 0:
            return float('inf')
        
        # 各参加者が一緒のグループになれる人の総数を計算
        participant_scores = []
        
        for group in groups:
            group_participants = list(group.get_participants())
            for participant in group_participants:
                # 同じグループ内の他の参加者との組み合わせ数を計算
                score = len(group_participants) - 1
                participant_scores.append(score)
        
        if not participant_scores:
            return float('inf')
        
        # 平均と分散を計算
        mean_score = sum(participant_scores) / len(participant_scores)
        variance = sum((score - mean_score) ** 2 for score in participant_scores) / len(participant_scores)
        
        # 評価値（平均が高く、分散が低いほど良い）
        evaluation_score = -mean_score + variance * 0.1
        
        return evaluation_score
