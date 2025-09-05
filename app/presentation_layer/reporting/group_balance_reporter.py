import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def _extract_participant_name(full_name: str) -> str:
    match = re.match(r'(.+?)\([^)]+\)', full_name)
    return match.group(1) if match else full_name


def _analyze_group_balance(result_file: str) -> Dict[str, Dict[str, int]]:
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cooccurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for session_groups in data['program']:
        for group in session_groups:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    name1 = _extract_participant_name(group[i])
                    name2 = _extract_participant_name(group[j])
                    cooccurrence[name1][name2] += 1
                    cooccurrence[name2][name1] += 1

    return cooccurrence


def _get_all_participants(cooccurrence: Dict[str, Dict[str, int]]) -> List[str]:
    participants = set()
    for p in cooccurrence.keys():
        participants.add(p)
        for other in cooccurrence[p].keys():
            participants.add(other)
    return sorted(list(participants))


def _generate_markdown_table(cooccurrence: Dict[str, Dict[str, int]], output_file: str) -> None:
    participants = _get_all_participants(cooccurrence)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("| 参加者 |")
        for participant in participants:
            f.write(f" {participant} |")
        f.write("\n")
        f.write("|--------|")
        for _ in participants:
            f.write("--------|")
        f.write("\n")
        for participant in participants:
            f.write(f"| {participant} |")
            for other in participants:
                if participant == other:
                    f.write(" - |")
                else:
                    count = cooccurrence[participant].get(other, 0)
                    f.write(f" {count} |")
            f.write("\n")


def _generate_csv_table(cooccurrence: Dict[str, Dict[str, int]], output_file: str) -> None:
    participants = _get_all_participants(cooccurrence)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("参加者,")
        f.write(",".join(participants))
        f.write("\n")
        for participant in participants:
            f.write(f"{participant},")
            row: List[str] = []
            for other in participants:
                if participant == other:
                    row.append("-")
                else:
                    row.append(str(cooccurrence[participant].get(other, 0)))
            f.write(",".join(row))
            f.write("\n")


def generate_group_balance_tables(result_json_path: str, outputs_dir: Path) -> None:
    print("\nグループのバランス分析を開始...")
    cooccurrence = _analyze_group_balance(result_json_path)
    participants = _get_all_participants(cooccurrence)
    print(f"参加者数: {len(participants)}")

    outputs_dir.mkdir(parents=True, exist_ok=True)
    markdown_file = str(outputs_dir / "group_balance_table.md")
    csv_file = str(outputs_dir / "group_balance_table.csv")
    _generate_markdown_table(cooccurrence, markdown_file)
    _generate_csv_table(cooccurrence, csv_file)

    max_co, max_pair, total_co, pair_cnt = 0, None, 0, 0
    for i, p in enumerate(participants):
        for j in range(i + 1, len(participants)):
            other = participants[j]
            c = cooccurrence[p].get(other, 0)
            total_co += c
            pair_cnt += 1
            if c > max_co:
                max_co = c
                max_pair = (p, other)

    if max_pair is not None:
        print(f"最も多く一緒になったペア: {max_pair[0]} - {max_pair[1]} ({max_co}回)")
    if pair_cnt > 0:
        print(f"平均共起回数: {total_co / pair_cnt:.2f}")

    per_person_avg: Dict[str, float] = {}
    for p in participants:
        total = sum(cooccurrence[p].values())
        per_person_avg[p] = total / (len(participants) - 1)
    print("\n各参加者の平均共起回数:")
    for p, avg in sorted(per_person_avg.items(), key=lambda x: x[1], reverse=True):
        print(f"  {p}: {avg:.2f}")
    print("\n✅ 分析完了！")
    print(f"📊 Markdownテーブル: {markdown_file}")
    print(f"📈 CSVテーブル: {csv_file}")


def generate_session_group_matrix_csv(result_json_path: str, outputs_dir: Path) -> None:
    """
    セッションごとに、列=グループ(A,B,...)、行=メンバー名のCSVを出力する。
    形式:
    Session1\n
    A,B,C,...\n
    name1,name2,...\n
    (空行)\n
    Session2 ...
    """
    outputs_dir.mkdir(parents=True, exist_ok=True)
    matrix_csv = outputs_dir / "session_groups_matrix.csv"

    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sessions = data.get('program', [])

    with open(matrix_csv, 'w', encoding='utf-8') as out:
        for s_idx, session_groups in enumerate(sessions):
            out.write(f"Session{s_idx + 1}\n")
            # グループ列ヘッダ A,B,C,...
            num_groups = len(session_groups)
            headers = [chr(ord('A') + i) for i in range(num_groups)]
            out.write(", ".join(headers) + "\n")

            # 最大人数に合わせて行を埋める
            max_rows = max((len(g) for g in session_groups), default=0)
            for r in range(max_rows):
                row = []
                for g in session_groups:
                    if r < len(g):
                        row.append(_extract_participant_name(g[r]))
                    else:
                        row.append("")
                out.write(", ".join(row) + "\n")

            # セッション間の空行
            if s_idx != len(sessions) - 1:
                out.write("\n")

    print(f"🧾 セッション別グループCSV: {str(matrix_csv)}")


