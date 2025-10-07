import random
import time
from typing import Dict, List, Tuple

from ...domain_layer.services.group_assigner import GroupAssigner
from ...domain_layer.entities.program import Program
from ...domain_layer.first_class_collections.participants import Participants
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.entities.group import Group
from ...domain_layer.entities.participant import PositionType

from .group_assigner_heuristic import GroupAssignerHeuristic


class GroupAssignerHybridGA(GroupAssigner):
    """
    Heuristicで複数の初期解を作り、GAで最適化するハイブリッドアサイナー。
    表現: individual[session_idx] = list[list[int]] （各グループのparticipant-indexの配列）
    """

    def __init__(
        self,
        num_heuristic_seeds: int = 10,
        generations: int = 500,
        population_size: int = 40,
        mutation_rate: float = 0.08,
        time_budget_seconds: float = 3.0,
        heuristic_iterations: int = 200,
    ) -> None:
        self.num_heuristic_seeds = num_heuristic_seeds
        self.generations = generations
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.time_budget_seconds = time_budget_seconds
        self.heuristic_iterations = heuristic_iterations

    # ========= public =========
    def assign_groups(self, program: Program) -> Dict[int, Groups]:
        sessions = program.get_sessions()
        sessions_list = [s for s in sessions]

        # 1) ヒューリスティックで初期解を複数作成
        seeds = self._make_heuristic_seeds(program, self.num_heuristic_seeds)

        # 2) GAの設定／補助
        def to_index_solution(groups_dict: Dict[int, Groups]) -> List[List[List[int]]]:
            sols: List[List[List[int]]] = []
            for session_index, session in enumerate(sessions_list):
                g_list: List[List[int]] = []
                g_groups = groups_dict[session_index]
                for group in g_groups:
                    idxs: List[int] = []
                    for p in group.get_participants():
                        # 参加者インデックスへ変換
                        idxs.append(self._find_index_in_session(session, p))
                    g_list.append(idxs)
                sols.append(g_list)
            return sols

        population: List[List[List[List[int]]]] = []
        for seed in seeds:
            population.append(to_index_solution(seed))

        # 不足分をランダム生成（ヒューリスティック個体を軽く撹拌）
        while len(population) < self.population_size:
            base = random.choice(population)
            population.append(self._mutate_indices(base, sessions_list, force=True))

        start_time = time.time()
        best = max(population, key=lambda ind: self._fitness(ind, sessions_list))

        # 3) GA ループ
        for _ in range(self.generations):
            scored = sorted(((self._fitness(ind, sessions_list), ind) for ind in population), reverse=True)
            elites = [ind for (_, ind) in scored[: max(2, self.population_size // 4)]]
            new_pop: List[List[List[List[int]]]] = elites.copy()

            # 交叉＋突然変異
            while len(new_pop) < self.population_size:
                p1, p2 = random.sample(elites, 2) if len(elites) >= 2 else (best, random.choice(population))
                child = self._crossover(p1, p2, sessions_list)
                child = self._mutate_indices(child, sessions_list)
                new_pop.append(child)

            population = new_pop
            cur_best = max(population, key=lambda ind: self._fitness(ind, sessions_list))
            if self._fitness(cur_best, sessions_list) > self._fitness(best, sessions_list):
                best = cur_best
            if time.time() - start_time > self.time_budget_seconds:
                break

        # 4) best 個体を Groups に変換して返却
        return self._indices_to_groups(best, sessions_list)

    # ========= heuristic seeds =========
    def _make_heuristic_seeds(self, program: Program, num: int) -> List[Dict[int, Groups]]:
        seeds: List[Dict[int, Groups]] = []
        for i in range(num):
            random.seed(int(time.time() * 1000 + i) % 2**32)
            heur = GroupAssignerHeuristic(max_iterations=self.heuristic_iterations)
            seeds.append(heur.assign_groups(program))
        return seeds

    # ========= GA operators / helpers =========
    def _fitness(self, individual: List[List[List[int]]], sessions_list) -> float:
        """大きいほど良い。サイズ違反のない範囲で、ペア再会の少なさ・均等性・ラボ重複の少なさを評価。"""
        W_SIZE = 1_000_000
        W_PAIR = 100
        W_SPREAD = 500  # 分散を強めに抑制
        W_RANGE = 100   # 最大-最小の偏りも抑制
        W_LAB = 50      # lab重複を強く抑制

        from collections import defaultdict
        import math

        size_pen = 0.0
        pair_pen = 0.0
        spread_pen = 0.0
        range_pen = 0.0
        lab_pen = 0.0

        mates = {}
        together_count = defaultdict(int)

        for s_idx, session in enumerate(sessions_list):
            session_groups = individual[s_idx]

            # サイズ違反
            for g in session_groups:
                if not (session.get_min() <= len(g) <= session.get_max()):
                    size_pen += 1

            # ペア/均等性/ラボ
            for g in session_groups:
                ids = []
                for idx in g:
                    pid = session.get_participants().get_participant_by_index(idx).get_id().as_str()
                    mates.setdefault(pid, set())
                    ids.append(pid)
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        a, b = ids[i], ids[j]
                        pair = tuple(sorted([a, b]))
                        together_count[pair] += 1
                        mates[a].add(b)
                        mates[b].add(a)

                # ラボ重複（累積罰）
                lab_count = {}
                for idx in g:
                    for lab in session.get_participants().get_participant_by_index(idx).get_lab():
                        lab_count[lab] = lab_count.get(lab, 0) + 1
                for c in lab_count.values():
                    if c > 1:
                        lab_pen += (c - 1) * c // 2

        for cnt in together_count.values():
            if cnt > 1:
                pair_pen += (cnt - 1) * cnt // 2

        if mates:
            counts = [len(s) for s in mates.values()]
            avg = sum(counts) / len(counts)
            var = sum((c - avg) ** 2 for c in counts) / len(counts)
            spread_pen += var
            if counts:
                range_pen += (max(counts) - min(counts))

        total_penalty = (
            W_SIZE * size_pen +
            W_PAIR * pair_pen +
            W_SPREAD * spread_pen +
            W_RANGE * range_pen +
            W_LAB * lab_pen
        )
        return -total_penalty

    def _crossover(self, p1: List[List[List[int]]], p2: List[List[List[int]]], sessions_list) -> List[List[List[int]]]:
        """lab重複を減らす交叉。各グループについて、親1/親2からランダムに選び、
        facultyは各グループに1人必ず入るようにする。"""
        child: List[List[List[int]]] = []
        for s_idx, session in enumerate(sessions_list):
            gnum = session.get_group_num()
            c_session: List[List[int]] = []

            # ヘルパー: 職位取得
            def pos_of(idx: int):
                return session.get_participants().get_participant_by_index(idx).get_position()

            # ヘルパー: lab重複を計算
            def calculate_lab_duplicates(group: List[int]) -> int:
                lab_count = {}
                for idx in group:
                    for lab in session.get_participants().get_participant_by_index(idx).get_lab():
                        lab_count[lab] = lab_count.get(lab, 0) + 1
                return sum((c - 1) * c // 2 for c in lab_count.values() if c > 1)

            for g in range(gnum):
                g1 = list(p1[s_idx][g])
                g2 = list(p2[s_idx][g])
                
                # 両親のグループサイズの平均を目標サイズとする
                target_size = (len(g1) + len(g2)) // 2
                if target_size < session.get_min():
                    target_size = session.get_min()
                elif target_size > session.get_max():
                    target_size = session.get_max()

                assembled: List[int] = []
                used = set()
                
                # まずfacultyを1人選ぶ（各グループに必ず1人）
                faculty_candidates = []
                for idx in g1 + g2:
                    if pos_of(idx) == PositionType.FACULTY and idx not in used:
                        faculty_candidates.append(idx)
                
                if faculty_candidates:
                    # lab重複が少ないfacultyを選ぶ
                    best_faculty = min(faculty_candidates, 
                                     key=lambda idx: calculate_lab_duplicates([idx]))
                    assembled.append(best_faculty)
                    used.add(best_faculty)
                
                # 残りのメンバーを選ぶ（lab重複を最小化）
                remaining_candidates = [idx for idx in g1 + g2 if idx not in used]
                random.shuffle(remaining_candidates)
                
                for idx in remaining_candidates:
                    if len(assembled) >= target_size:
                        break
                    assembled.append(idx)
                    used.add(idx)

                # 足りない場合はセッション全体から補完
                if len(assembled) < target_size:
                    all_indices = list(range(session.get_participants().length()))
                    random.shuffle(all_indices)
                    for i in all_indices:
                        if len(assembled) >= target_size:
                            break
                        if i in used:
                            continue
                        assembled.append(i)
                        used.add(i)

                c_session.append(assembled)

            child.append(self._repair_session(session, c_session))
        return child

    def _mutate_indices(self, individual: List[List[List[int]]], sessions_list, force: bool = False) -> List[List[List[int]]]:
        child = []
        for s_idx, session in enumerate(sessions_list):
            groups = [list(g) for g in individual[s_idx]]
            if force or random.random() < self.mutation_rate:
                if len(groups) >= 2:
                    g1, g2 = random.sample(range(len(groups)), 2)
                    if groups[g1] and groups[g2]:
                        # ランダムに2人を選んで入れ替え（職位制約なし）
                        a = random.choice(groups[g1])
                        b = random.choice(groups[g2])
                        i1 = groups[g1].index(a)
                        i2 = groups[g2].index(b)
                        groups[g1][i1], groups[g2][i2] = groups[g2][i2], groups[g1][i1]
            child.append(self._repair_session(session, groups))
        return child

    def _repair_session(self, session, groups: List[List[int]]) -> List[List[int]]:
        """重複排除と min/max を満たすよう軽い修復。"""
        # 重複除去
        seen = set()
        for g in groups:
            i = 0
            while i < len(g):
                if g[i] in seen:
                    g.pop(i)
                else:
                    seen.add(g[i])
                    i += 1
        # 未配置を回収
        all_idx = list(range(session.get_participants().length()))
        missing = [i for i in all_idx if i not in seen]

        # 小さいグループから順に補充
        groups_sorted = sorted(range(len(groups)), key=lambda k: len(groups[k]))
        for idx in missing:
            for gi in groups_sorted:
                if len(groups[gi]) < session.get_max():
                    groups[gi].append(idx)
                    break

        # 超過調整（大きい→小さいへ移す）
        changed = True
        while changed:
            changed = False
            bigs = [i for i, g in enumerate(groups) if len(g) > session.get_max()]
            smalls = [i for i, g in enumerate(groups) if len(g) < session.get_min()]
            if not bigs and not smalls:
                break
            for bi in bigs:
                for si in smalls:
                    if groups[bi] and len(groups[si]) < session.get_min():
                        groups[si].append(groups[bi].pop())
                        changed = True
                        break

        # Faculty の均等化（各グループに必ず1名のFacultyを配置）
        def is_fac(idx: int) -> bool:
            return (
                session.get_participants()
                .get_participant_by_index(idx)
                .get_position()
                == PositionType.FACULTY
            )

        def fac_count(g: List[int]) -> int:
            return sum(1 for i in g if is_fac(i))

        # 各グループにfacultyが1人いるかチェック
        for gi, g in enumerate(groups):
            if fac_count(g) == 0:
                # facultyがいないグループにはfacultyを1人配置
                # セッション全体からfacultyを探す
                all_faculty = [i for i in range(session.get_participants().length()) if is_fac(i)]
                available_faculty = [i for i in all_faculty if i not in seen]
                
                if available_faculty:
                    # ランダムにfacultyを選んで配置
                    faculty_to_add = random.choice(available_faculty)
                    groups[gi].append(faculty_to_add)
                    seen.add(faculty_to_add)
                else:
                    # 他のグループからfacultyを移動
                    for gj, other_g in enumerate(groups):
                        if gi != gj and fac_count(other_g) >= 2:
                            # 他のグループからfacultyを1人移動
                            fac_idx = next((k for k, idx in enumerate(other_g) if is_fac(idx)), None)
                            if fac_idx is not None:
                                moving_faculty = other_g.pop(fac_idx)
                                groups[gi].append(moving_faculty)
                                break

        return groups

    # ========= conversion =========
    def _find_index_in_session(self, session, participant) -> int:
        fc = session.get_participants()
        for i in range(fc.length()):
            if fc.get_participant_by_index(i).get_id().as_str() == participant.get_id().as_str():
                return i
        # フォールバック（理論上到達しない想定）
        return 0

    def _indices_to_groups(self, individual: List[List[List[int]]], sessions_list) -> Dict[int, Groups]:
        results: Dict[int, Groups] = {}
        for s_idx, session in enumerate(sessions_list):
            group_objs = Groups.empty()
            for g in individual[s_idx]:
                ps = Participants.empty()
                for idx in g:
                    ps = ps.add_participant(session.get_participants().get_participant_by_index(idx))
                group_objs = group_objs.add_group(Group.create(ps))
            results[s_idx] = group_objs
        return results


