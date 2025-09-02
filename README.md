## GroupAssigner 概要

参加者を複数セッション・複数グループへ公平に割り当てるツールです。ヒューリスティックで初期解を生成し、必要に応じてハイブリッドGA（Heuristic + GA）で最適化します。出力として JSON の結果および共起（同じグループになった回数）テーブルを Markdown/CSV で生成します。

### 特徴
- 職位（Faculty/Doctoral/Master/Bachelor）ごとの受け入れ枠を、A→…→G→G→…→A→A…のジグザグ配分で事前計算し均等化（容量 `min/max` を尊重）
- セッション設定の `group_num`・`min`・`max` に従ってグループを生成
- 公平性（全セッション横断の共起人数の分散・レンジ）をハイブリッドGAの評価関数で抑制
- 実行時に共起テーブル（Markdown/CSV）を自動生成

---

## 入力例（シンプル）

`app/inputs/input.json` の最小構成はこれだけです。

```json
{
  "participants": [
    {"name": "P01", "position": "Faculty",  "lab": ["LabA"]},
    {"name": "P02", "position": "Bachelor", "lab": ["LabB", "LabC"]},
    {"name": "P03", "position": "Doctoral", "lab": ["LabD"]},
    {"name": "P04", "position": "Master",   "lab": ["LabB"]}
  ],
  "sessions": [
    {"group_num": 2, "min": 2, "max": 3},
    {"group_num": 2, "min": 2, "max": 3}
  ]
}
```

補足:
- `position` は `Faculty | Doctoral | Master | Bachelor` のいずれか。
- `lab` は指導教員名(文字列)の配列（空配列も可）。
- 参加者は全セッション共通、各セッションのグループ数/下限/上限は `sessions` で指定します。

---

## 動作環境
- Docker / Docker Compose
- Python 3.11（Docker 内で使用）

---

## 使い方（Docker）

1) コンテナを起動

```bash
docker compose up app
```

初回はイメージのビルドが行われ、その後 `app` サービスが `app.main` を実行します。

2) 入力ファイル

- 入力 JSON: `app/inputs/test_input.json`（編集して実行）

3) 生成物の確認

- 結果 JSON: `app/outputs/result.json`
- 共起テーブル（Markdown）: `app/outputs/group_balance_table.md`
- 共起テーブル（CSV）: `app/outputs/group_balance_table.csv`

4) 孤児コンテナの整理（必要時）

```bash
docker compose up --remove-orphans app
```

---

## ディレクトリ構成（主要）

```
app/
  main.py                              # エントリポイント（ユースケース実行・結果保存・レポート呼び出し）
  inputs/                              # 入力ファイル (input.json)
  outputs/                             # 生成物出力先（result.json / MD / CSV）
  infrastructure_layer/
    domain_implementations/
      group_assigner_heuristic.py      # ヒューリスティック割当（ジグザグ受け入れ枠・重複/ラボ回避）
      group_assigner_hybrid_ga.py      # Heuristicシード + GA（職位セーフ交叉/突然変異、公平性分散/レンジ罰則）
  presentation_layer/
    reporting/
      group_balance_reporter.py        # 共起分析とテーブル生成
    output_formatter/
      result_postprocessor.py          # result.json への統計値（平均/分散）付加
```

---

## アルゴリズム概要（簡易）

1. 初期解の生成
   - セッション設定の `group_num`・`min`・`max` に従いグループ容量を決定
   - 職位ごとの受け入れ枠をジグザグで事前配分（端点は一度留まって折り返し）
   - 枠に沿って、ラボ重複・既出ペアを避けつつスコア最小のグループに配置

2. 局所探索
   - 同一職位間の入替など、小規模な変更で評価値（平均高・分散低）改善を試行

3. GA
   - 既存ヒューリスティックで複数シードを生成して初期集団に投入
   - 交叉: グループごとの職位別目標人数を保ったまま、同職位のみで構成
   - 突然変異: 同職位同士のみ入れ替え（職位セーフ）
   - 修復: 重複除去・min/max充足、教員の均等配分
   - 評価: サイズ違反＞ペア重複＞公平性（分散/レンジ）＞ラボ重複の順に罰則を加算

4. 評価/レポート
   - `result.json` に評価値と各参加者の重複人数（distinct_partners）を保存
   - `distinct_partners_avg` と `distinct_partners_variance`（平均・分散）を付加
   - 共起テーブル（MD/CSV）を自動生成

---

## カスタマイズ

- 入力データ: `app/inputs/test_input.json` を編集
- アルゴリズム切替: `app/main.py` 内の `group_assigner` のコメントアウト切替
- 出力先: 既定は `app/outputs/`。変更は `app/main.py` の出力パスを編集

---

## その他のアルゴリズム（おまけ）

本リポジトリにはヒューリスティック以外にもいくつかの実装が含まれています。`app/main.py` の `group_assigner` をコメントアウトで切り替えて試せます。

- OR-Tools 標準版: `app/infrastructure_layer/domain_implementations/group_assigner_ortools.py`
  - 制約最適化により解を探索する基本実装。

- OR-Tools 緩和版: `app/infrastructure_layer/domain_implementations/group_assigner_ortools_relaxed.py`
  - いくつかの制約を緩め、可解性・速度を重視。

- OR-Tools 高度版: `app/infrastructure_layer/domain_implementations/group_assigner_ortools_advanced.py`
  - 追加ヒューリスティックや調整を入れた発展版。

- ハイブリッドGA: `app/infrastructure_layer/domain_implementations/group_assigner_hybrid_ga.py`
  - Heuristicシード + GA最適化（職位セーフ交叉/突然変異、公平性分散/レンジ罰則）

切り替え例（`app/main.py`）:

```python
# 1. ヒューリスティック（既定例）
group_assigner = GroupAssignerHeuristic(max_iterations=1000)

# 2. ハイブリッドGA（公平性最重視）
# group_assigner = GroupAssignerHybridGA(num_heuristic_seeds=10, generations=500)

# 3. 緩和版 OR-Tools
# group_assigner = GroupAssignerORToolsRelaxed()

# 4. OR-Tools 標準
# group_assigner = GroupAssignerORTools()

# 5. OR-Tools 高度版
# group_assigner = GroupAssignerORToolsAdvanced()
```

それぞれで出力形式は同じ（`app/outputs/` 以下に `result.json` とテーブル）です。

---

