from collections import defaultdict
import random
import logging
import math
import time

from ...domain_layer.services.group_assigner import GroupAssigner
from ...domain_layer.entities.program import Program
from ...domain_layer.first_class_collections.participants import Participants
from ...domain_layer.first_class_collections.groups import Groups
from ...domain_layer.entities.group import Group
from ...domain_layer.entities.participant import PositionType

logger = logging.getLogger(__name__)

class GroupAssignerGA(GroupAssigner):
    """
    Group assigner using Genetic Algorithm (GA).
    """
    def assign_groups(self, program: Program) -> dict[int, Groups]:
        sessions = program.get_sessions()
        sessions_list = [s for s in sessions]

        # Utility: compute per-group targets per position based on group sizes
        def compute_position_targets(session, group_sizes):
            # 2次元のアポーション: cell[g][pos] = floor(share), 余りは各posの大きいfrac順に、かつ各groupのサイズ上限まで割当
            participants_fc = session.get_participants()
            total_by_pos = {pos: 0 for pos in PositionType}
            for i in range(participants_fc.length()):
                total_by_pos[participants_fc.get_participant_by_index(i).get_position()] += 1
            N = sum(group_sizes)

            G = len(group_sizes)
            # 初期化
            cell_base = [{pos: 0 for pos in PositionType} for _ in range(G)]
            cell_frac = [{pos: 0.0 for pos in PositionType} for _ in range(G)]
            row_sum = [0 for _ in range(G)]
            rem_pos = {pos: total_by_pos[pos] for pos in PositionType}

            # floor割当とfrac保存
            for gi, gsize in enumerate(group_sizes):
                for pos, T in total_by_pos.items():
                    share = (T * gsize) / max(1, N)
                    b = int(share)
                    f = share - b
                    cell_base[gi][pos] = b
                    cell_frac[gi][pos] = f
                    row_sum[gi] += b
                    rem_pos[pos] -= b

            # 余りを各posごとにfrac降順で、かつ行の容量内で配分
            for pos in PositionType:
                if rem_pos[pos] <= 0:
                    continue
                # frac大きい順のgroupインデックス
                order = sorted(range(G), key=lambda gi: cell_frac[gi][pos], reverse=True)
                idx = 0
                guard = 0
                while rem_pos[pos] > 0 and guard < 10000:
                    gi = order[idx]
                    if row_sum[gi] < group_sizes[gi]:
                        cell_base[gi][pos] += 1
                        row_sum[gi] += 1
                        rem_pos[pos] -= 1
                    idx = (idx + 1) % G
                    guard += 1

            # 最終チェック: 行和はgroup_sizesに一致、列和はtotal_by_posに一致のはず
            return cell_base

        def build_groups_from_targets(session, targets, source_by_pos):
            # source_by_pos: pos -> list of indices available (unique), already shuffled
            participants_fc = session.get_participants()
            fallback_by_pos = {pos: [] for pos in PositionType}
            for i in range(participants_fc.length()):
                p = participants_fc.get_participant_by_index(i)
                fallback_by_pos[p.get_position()].append(i)
            # Remove already present indices from fallback
            present = set([idx for lst in source_by_pos.values() for idx in lst])
            for pos in PositionType:
                fallback_by_pos[pos] = [i for i in fallback_by_pos[pos] if i not in present]

            groups = [[] for _ in range(len(targets))]
            for gi, target in enumerate(targets):
                for pos, need in target.items():
                    for _ in range(need):
                        if source_by_pos.get(pos) and len(source_by_pos[pos]) > 0:
                            groups[gi].append(source_by_pos[pos].pop())
                        elif fallback_by_pos[pos]:
                            groups[gi].append(fallback_by_pos[pos].pop())
                        else:
                            # fallback: pick any remaining index of same pos from other groups if any
                            for sj in range(len(groups)):
                                if sj == gi:
                                    continue
                                # try to steal from future allocations (rare)
                                pass
            return groups

        def equal_group_sizes(session):
            # 参加人数 N からグループ数 G を G = ceil(N/4) で決定（5人を出さない）。
            N = session.get_participants().length()
            min_sz = session.get_min()
            max_sz = session.get_max()

            # 5人を避けたい場合は G は少なくとも ceil(N/4)
            import math
            G = max(1, math.ceil(N / 4))

            # 均等配分（q, r で qかq+1のみ）
            q, r = divmod(N, G)
            sizes = [q + 1 if i < r else q for i in range(G)]

            # min/max に収める（必要ならGを増やして再配分）
            guard = 0
            while (any(sz > max_sz for sz in sizes) or any(sz < min_sz for sz in sizes)) and guard < 100:
                G += 1
                q, r = divmod(N, G)
                sizes = [q + 1 if i < r else q for i in range(G)]
                guard += 1

            return sizes
        # participants = program.get_participants()

        population_size = 50
        generations = 2000
        mutation_rate = 0.05
        time_budget_seconds = 2.0
        start_time = time.time()

        def create_individual():
            """
            全てのセッションを表現する個体を生成
            形式: list[list[list[ParticipantId]]]
            """

            individual = []
            for session in sessions:
                # 初期個体: 職位ごとに均等配分となるように構築
                group_sizes = equal_group_sizes(session)
                targets = compute_position_targets(session, group_sizes)
                # build source_by_pos from all participants
                source_by_pos = {pos: [] for pos in PositionType}
                participants_fc = session.get_participants()
                for i in range(participants_fc.length()):
                    pos = participants_fc.get_participant_by_index(i).get_position()
                    source_by_pos[pos].append(i)
                for pos in PositionType:
                    random.shuffle(source_by_pos[pos])
                session_groups = build_groups_from_targets(session, targets, source_by_pos)
                individual.append(session_groups)
            return individual
        
        def repair_session_groups(session, session_groups):
            # Compute desired group sizes (keep current sizes)
            group_sizes = [len(g) for g in session_groups]
            N = sum(group_sizes)
            participants_fc = session.get_participants()

            # Map p_index -> position
            pos_by_index = {}
            for i in range(participants_fc.length()):
                pos_by_index[i] = participants_fc.get_participant_by_index(i).get_position()

            # Total per position
            total_by_pos = {pos: 0 for pos in PositionType}
            for i in range(participants_fc.length()):
                total_by_pos[pos_by_index[i]] += 1

            # Apportion targets per group by Hamilton method proportional to group size
            # targets[g][pos] -> int
            targets = []
            for gi, gsize in enumerate(group_sizes):
                targets.append({pos: 0 for pos in PositionType})
            for pos, T in total_by_pos.items():
                # base allocations
                bases = []
                fracs = []
                s = 0
                for gsize in group_sizes:
                    share = (T * gsize) / max(1, N)
                    b = int(share)
                    f = share - b
                    bases.append(b)
                    fracs.append(f)
                    s += b
                rem = T - s
                # distribute remaining to groups with largest fractional parts
                order = sorted(range(len(group_sizes)), key=lambda k: fracs[k], reverse=True)
                for k in range(rem):
                    targets[order[k]][pos] += 1
                for gi in range(len(group_sizes)):
                    targets[gi][pos] += bases[gi]

            # Helper to get counts in group
            def group_pos_counts(g):
                cnt = {pos: 0 for pos in PositionType}
                for idx in g:
                    cnt[pos_by_index[idx]] += 1
                return cnt

            # Build quick lookups of indices by position per group
            def indices_by_pos(g):
                mp = {pos: [] for pos in PositionType}
                for idx in g:
                    mp[pos_by_index[idx]].append(idx)
                return mp

            min_size = session.get_min()
            max_size = session.get_max()

            # Iterative repair: try swaps preferred, then moves if sizes allow
            for _ in range(200):
                changed = False
                counts = [group_pos_counts(g) for g in session_groups]
                # Check done
                ok = True
                for gi, g in enumerate(session_groups):
                    for pos in PositionType:
                        if counts[gi][pos] != targets[gi][pos]:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    break

                # Try swaps
                for gi in range(len(session_groups)):
                    g1 = session_groups[gi]
                    c1 = counts[gi]
                    t1 = targets[gi]
                    excess_pos = [pos for pos in PositionType if c1[pos] > t1[pos]]
                    deficit_pos = [pos for pos in PositionType if c1[pos] < t1[pos]]
                    if not excess_pos:
                        continue
                    idx_by_pos_g1 = indices_by_pos(g1)
                    for gj in range(len(session_groups)):
                        if gi == gj:
                            continue
                        g2 = session_groups[gj]
                        c2 = counts[gj]
                        t2 = targets[gj]
                        excess_pos_g2 = [pos for pos in PositionType if c2[pos] > t2[pos]]
                        deficit_pos_g2 = [pos for pos in PositionType if c2[pos] < t2[pos]]
                        if not deficit_pos_g2 and not excess_pos_g2:
                            continue
                        idx_by_pos_g2 = indices_by_pos(g2)
                        did_swap = False
                        for pa in excess_pos:
                            # prefer swap against a position that g1 needs and g2 has excess
                            for pb in deficit_pos:
                                if pb in excess_pos_g2 and pa in deficit_pos_g2:
                                    # swap pa from g1 with pb from g2
                                    if idx_by_pos_g1[pa] and idx_by_pos_g2[pb]:
                                        ia = idx_by_pos_g1[pa].pop()
                                        ib = idx_by_pos_g2[pb].pop()
                                        g1.remove(ia); g2.append(ia)
                                        g2.remove(ib); g1.append(ib)
                                        # update counts minimally
                                        counts[gi][pa] -= 1; counts[gi][pb] += 1
                                        counts[gj][pb] -= 1; counts[gj][pa] += 1
                                        changed = True
                                        did_swap = True
                                        break
                            if did_swap:
                                break
                        if did_swap:
                            break
                    if changed:
                        break
                if changed:
                    continue

                # Try single moves if sizes allow
                for gi in range(len(session_groups)):
                    g1 = session_groups[gi]
                    if len(g1) <= min_size:
                        continue
                    c1 = counts[gi]
                    t1 = targets[gi]
                    excess_pos = [pos for pos in PositionType if c1[pos] > t1[pos]]
                    if not excess_pos:
                        continue
                    idx_by_pos_g1 = indices_by_pos(g1)
                    for gj in range(len(session_groups)):
                        if gi == gj:
                            continue
                        g2 = session_groups[gj]
                        if len(g2) >= max_size:
                            continue
                        c2 = counts[gj]
                        t2 = targets[gj]
                        deficit_pos_g2 = [pos for pos in PositionType if c2[pos] < t2[pos]]
                        if not deficit_pos_g2:
                            continue
                        # move one participant with any excess pos matching a deficit in g2
                        moved = False
                        for pa in excess_pos:
                            if pa in deficit_pos_g2 and idx_by_pos_g1[pa]:
                                ia = idx_by_pos_g1[pa].pop()
                                g1.remove(ia); g2.append(ia)
                                counts[gi][pa] -= 1
                                counts[gj][pa] += 1
                                changed = True
                                moved = True
                                break
                        if moved:
                            break
                    if changed:
                        break
                if not changed:
                    break

            return session_groups
        
        def fitness(individual):
            """
            個体の適応度（最大化）。重みづけ: Position最優先 > ペア再会 > Lab重複。
            罰則は大きいほど悪いので、最終的に -total_penalty を返す。
            """
            # 重み（階層的優先度を表現）
            W_SIZE   = 1_000_000    # サイズ違反は致命的
            W_REQ    = 10_000       # ファカルティ要件（グローバル制約）
            W_POS    = 0            # 職位は交叉/修復で担保するため評価から除外
            W_PAIR   = 100          # 次に重要（同一ペア再会の少なさ）
            W_SPREAD = 40           # 異なる同席人数の分散（均等性）
            W_LAB    = 5            # 最後に重要（ラボ重複）

            pos_pen = 0.0
            pair_pen = 0.0
            spread_pen = 0.0
            lab_pen = 0.0
            size_pen = 0.0
            req_pen = 0.0

            together_count = defaultdict(int)
            # 各人の「異なる同席相手」の集合
            mates = {}

            for (session_index, session) in enumerate(sessions):
                session_groups = individual[session_index]

                # サイズ違反
                for group in session_groups:
                    if not (session.get_min() <= len(group) <= session.get_max()):
                        size_pen += 1

                # グローバル制約の罰則（Domain Constraint 依存なし）
                # 教員必須
                for group in session_groups:
                    faculty_count = sum(
                        1 for p_index in group
                        if session.get_participants().get_participant_by_index(p_index).get_position() == PositionType.FACULTY
                    )
                    if faculty_count < 1:
                        req_pen += 1

                # 職位バランス（過半数超過＋偏り）
                for group in session_groups:
                    pos_count = {pos: 0 for pos in PositionType}
                    for p_index in group:
                        pos_count[session.get_participants().get_participant_by_index(p_index).get_position()] += 1
                    gsz = max(1, len(group))
                    limit = math.ceil(gsz / 2)
                    over = sum(max(0, c - limit) for c in pos_count.values())
                    pos_pen += 10 * over
                    max_c = max(pos_count.values())
                    min_c = min(pos_count.values())
                    pos_pen += 2 * max(0, max_c - min_c)

                # ラボ重複の罰
                for group in session_groups:
                    lab_count = {}
                    for p_index in group:
                        for lab in session.get_participants().get_participant_by_index(p_index).get_lab():
                            lab_count[lab] = lab_count.get(lab, 0) + 1
                    for c in lab_count.values():
                        if c > 1:
                            lab_pen += (c - 1) * c // 2

                # ペア再会カウント
                for group in session_groups:
                    # 異なる同席者の集合構築
                    ids = []
                    for idx in group:
                        pid = session.get_participants().get_participant_by_index(idx).get_id().as_str()
                        mates.setdefault(pid, set())
                        ids.append(pid)
                    for i in range(len(ids)):
                        for j in range(i + 1, len(ids)):
                            a, b = ids[i], ids[j]
                            # ペア回数
                            pair = tuple(sorted([a, b]))
                            together_count[pair] += 1
                            # 異なる同席相手
                            mates[a].add(b)
                            mates[b].add(a)

            # ペア再会の罰則（1回目は0、2回目以降を加算）
            for cnt in together_count.values():
                if cnt > 1:
                    # 2回目: 1, 3回目: 3, 4回目: 6, 5回目: 10... (累積的に重くなる)
                    pair_pen += (cnt - 1) * cnt // 2

            # 異なる同席人数の分散（均等性）
            if mates:
                counts = [len(s) for s in mates.values()]
                avg = sum(counts) / len(counts)
                var = sum((c - avg) ** 2 for c in counts) / len(counts)
                spread_pen += var

            total_penalty = (
                W_SIZE * size_pen +
                W_REQ  * req_pen +
                W_POS  * pos_pen +
                W_PAIR * pair_pen +
                W_SPREAD * spread_pen +
                W_LAB  * lab_pen
            )
            return -total_penalty
        
        def crossover(parent1, parent2):
            """
            交叉操作
            """
            child = []
            for session_index in range(len(parent1)):
                session = sessions_list[session_index]
                group_sizes = equal_group_sizes(session)
                targets = compute_position_targets(session, group_sizes)
                # ソースは職位ごとに、親1と親2の要素を結合（重複除去）
                source_by_pos = {pos: set() for pos in PositionType}
                for groups in (parent1[session_index], parent2[session_index]):
                    for g in groups:
                        for idx in g:
                            pos = session.get_participants().get_participant_by_index(idx).get_position()
                            source_by_pos[pos].add(idx)
                source_by_pos = {pos: list(lst) for pos, lst in source_by_pos.items()}
                for pos in PositionType:
                    random.shuffle(source_by_pos[pos])
                session_child = build_groups_from_targets(session, targets, source_by_pos)
                child.append(session_child)
            return child
        
        def mutate(individual):
            """
            突然変異操作
            """
            for session_index in range(len(individual)):
                session = sessions_list[session_index]
                if random.random() < mutation_rate:
                    groups = individual[session_index]
                    if len(groups) >= 2:
                        g1_idx, g2_idx = random.sample(range(len(groups)), 2)
                        g1, g2 = groups[g1_idx], groups[g2_idx]
                        if g1 and g2:
                            # 同一職位のみ入れ替える
                            # 構築: それぞれの職位のインデックスリスト
                            def by_pos(g):
                                mp = {pos: [] for pos in PositionType}
                                for idx in g:
                                    pos = session.get_participants().get_participant_by_index(idx).get_position()
                                    mp[pos].append(idx)
                                return mp
                            bp1 = by_pos(g1)
                            bp2 = by_pos(g2)
                            pos_choices = [pos for pos in PositionType if bp1[pos] and bp2[pos]]
                            if pos_choices:
                                pos = random.choice(pos_choices)
                                i1 = random.randrange(len(bp1[pos]))
                                i2 = random.randrange(len(bp2[pos]))
                                a = bp1[pos][i1]
                                b = bp2[pos][i2]
                                # 位置を見つけてスワップ
                                g1[g1.index(a)], g2[g2.index(b)] = b, a
                # 職位バランスの安全弁
                individual[session_index] = repair_session_groups(session, individual[session_index])
            return individual
        
        # Initialize population
        population = [create_individual() for _ in range(population_size)]

        for gen in range(generations):
            scored = sorted([(fitness(ind), ind) for ind in population], reverse=True)
            population = [ind for (_, ind) in scored[:population_size // 2]]
            new_population = []
            while len(new_population) < population_size:
                parents = random.sample(population, 2)
                child = crossover(parents[0], parents[1])
                child = mutate(child)
                new_population.append(child)
            population = new_population
            if time.time() - start_time > time_budget_seconds:
                break

        best_individual = max(population, key=fitness)

        results: dict[int, Groups] = {}
        for (session_index, session) in enumerate(sessions):
            # 最終出力前に職位配分の修復をもう一度適用（可能な限り完全バランスへ）
            best_individual[session_index] = repair_session_groups(session, best_individual[session_index])
            group_objs = Groups.empty()
            for group in best_individual[session_index]:
                ps = Participants.empty()
                for p_index in group:
                    ps = ps.add_participant(session.get_participants().get_participant_by_index(p_index))
                group_objs = group_objs.add_group(Group.create(ps))
            results[session_index] = group_objs

        return results