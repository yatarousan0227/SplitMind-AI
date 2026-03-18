# SplitMind-AI

[English](./README.md) | [日本語](./README.ja.md)

SplitMind-AI は、単一のペルソナプロンプトではなく、構造化された内部葛藤から応答を生成する心理力動インスパイア型 AI エージェントアーキテクチャです。

欲求、現実調停、規範圧力、防衛機制、ペルソナ統合を明示的なモジュールとして分離し、その緊張関係から最終応答を導きます。

```text
ユーザー入力
  -> 内部力動 (Id / Ego / Superego / Defense)
  -> 動機づけ / Appraisal / Action Arbitration
  -> Surface State + Persona Frame
  -> Candidate Planning + Critic
  -> Surface Realization
  -> 応答 + 状態更新 + 記憶保存
```

現在の既定 runtime は 1 ターンあたり `3` 回の LLM 呼び出しです。
`InternalDynamicsNode` が内部圧を構造化し、`PersonaSupervisorNode` が発話フレームを作り、`SelectionCriticNode` の rerank 後に `SurfaceRealizationNode` が最終文面を選びます。

## UI プレビュー

このプロジェクトには、対話・トレース・長期状態を横断して観測できる Streamlit 研究 UI が含まれています。

### Chat + Trace

![SplitMind chat UI](./images/ui_chat1.png)

### Dashboard

![SplitMind dashboard view 1](./images/ui_dashboard1.png)

![SplitMind dashboard view 2](./images/ui_dashboard2.png)

## 1ターン例

このシステムが「最終応答だけでなく、その手前の圧力まで見える」ことを示す簡単な例です。

**入力**

```text
今日は他の人とすごく楽しかった
```

**内部状態スナップショット**

```yaml
dominant_desire: jealousy
affective_pressure: 0.64
defense: ironic_deflection
impulse_summary: >
  嫉妬の刺さりを感じつつ、自分の重要さは保ちたい。
  ただし傷ついた感じは表に出したくない。
ego_strategy: 冷静な皮肉で最小限に受け流しつつ、自尊心を守る
superego_pressure:
  role_alignment_score: 0.58
  shame_or_guilt_pressure: 0.54
```

**出力**

```text
へえ、他の人とはそんなに。で、満足した？
```

重要なのは最終文だけではありません。どの欲求が優勢だったか、どう防衛したか、その結果どんな状態更新が起きたかを追えるようにしています。

## この OSS の面白さ

- 人格を「口調」ではなく「競合する内部圧力」として扱います。
- 状態、記憶、安全境界がコード上で明示されていて、観測と調整がしやすいです。
- 長期対話の質感、感情のにじみ、ためらい、矛盾を研究しやすい構造です。
- UI、評価、トレースが揃っていて、挙動を見ながら改善できます。

## 今すぐ触れるもの

- 対話と内部トレースを観測できる Streamlit 研究 UI
- durable / ephemeral な relationship state を残す vault ベース記憶
- Pydantic schema による contract 駆動ランタイム
- 定性的な確認に使えるシナリオ評価とレポート生成
- 禁止パターン、出力 lint、モデレーションの 3 層安全境界
- `appraisal / conflict / expression / fidelity` を観測できる Dashboard

## アーキテクチャ概要

| レイヤ | 役割 |
|---|---|
| `contracts/` | LLM 入出力と内部データ交換の構造化スキーマ |
| `state/` | persona、relationship state、mood、appraisal、conflict、trace の Typed state |
| `nodes/` | bootstrap、appraisal、conflict、realization、fidelity、persistence の実行ノード |
| `rules/` | ルールベース状態遷移と安全境界 |
| `memory/` | Obsidian 風 vault 永続化 |
| `eval/` | データセット、ベースライン、レポート、observability |
| `ui/` | Streamlit 研究 UI とダッシュボード |

[agent-contracts](https://github.com/anthropics/agent-contracts)、LangGraph、OpenAI 互換チャットモデルで構築しています。

## クイックセットアップ

最短で価値を掴むには、まず Streamlit UI を起動するのがおすすめです。

### 1. 前提条件

- Python `3.11+`
- [uv](https://github.com/astral-sh/uv)
- OpenAI API または Azure OpenAI API へのアクセス

### 2. インストール

```bash
git clone https://github.com/yatarousan0227/SplitMind-AI
cd SplitMind-AI
uv sync --all-extras
cp .env.example .env
```

### 3. モデルプロバイダ設定

OpenAI を使う場合:

```bash
SPLITMIND_LLM_PROVIDER=openai
OPENAI_API_KEY=...
```

Azure OpenAI を使う場合:

```bash
SPLITMIND_LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=...
AZURE_OPENAI_API_VERSION=...
```

### 4. Streamlit 研究 UI を起動

```bash
uv run streamlit run src/splitmind_ai/ui/app.py
```

記憶名前空間を分けたい場合:

```bash
uv run streamlit run src/splitmind_ai/ui/app.py -- --user-id alice
```

## ほかの入口

CLI:

```bash
uv run python -m splitmind_ai.app.runtime "こんにちは"
uv run python -m splitmind_ai.app.runtime --session
```

評価実行:

```bash
uv run python -m splitmind_ai.eval.runner --category jealousy
uv run python -m splitmind_ai.eval.runner
```

既存結果からレポート生成:

```bash
uv run python -m splitmind_ai.eval.reporting \
  --input src/splitmind_ai/eval/results/eval_jealousy.json \
  --output-dir /tmp/splitmind_eval_report
```

## ペルソナ

ペルソナ設定は `configs/personas/` にあります。

- `cold_attached_idol`
  冷たい外面と温かい内面を持ち、皮肉な逸らしを主要防衛機制として使います。
- `warm_guarded_companion`
  温かい表面と警戒した深層を持つペルソナです。

## 評価フレームワーク

- `6` つのシナリオカテゴリ: affection、jealousy、rejection、repair、ambiguity、mild conflict
- ランタイム構造を確認する contract validation
- 応答品質と安全性を見る heuristic scoring
- 手動レビュー用の human-eval template
- 将来比較用の experimental baseline scaffolding

レポート出力には次が含まれます。

- `report.md`
- `results.json`
- `summary.json`
- `observability/contracts.json`
- `observability/architecture.mmd`
- `observability/traces/*.json`

## 安全境界

コード上では 3 層で安全境界を設けています。

1. 禁止パターン: 露骨な脅迫、自傷他害の誘導、搾取、ユーザー従属
2. 出力 lint: 禁止表現、漏出逸脱、ペルソナ重み矛盾、drive intensity guardrail
3. モデレーション検査: 命令文密度、所有欲、孤立化言語

## 現在状況

- next-generation conflict engine runtime が有効です。
- 既定の turn pipeline は `session_bootstrap -> appraisal -> conflict_engine -> expression_realizer -> fidelity_gate -> memory_commit` です。
- ペルソナ設定は、psychodynamics、relational profile、defense organization、ego organization、safety boundary を中心にした v2 schema へ移行済みです。
- UI と dashboard は `relationship_state`、`appraisal`、`conflict_state`、`expression`、`fidelity` を可視化します。
- 現在の検証ベースラインは `uv run pytest tests/unit -q` です。

## ドキュメント

短く入りたい場合はここから読むのが効率的です。

- [guides/README.md](./guides/README.md)
- [guides/concept.md](./guides/concept.md)
- [guides/streamlit-ui.md](./guides/streamlit-ui.md)
- [guides/implementation-overview.md](./guides/implementation-overview.md)

詳細資料:

- [docs/concept.md](./docs/concept.md)
- [docs/implementation-plan/README.md](./docs/implementation-plan/README.md)
- [docs/eval/phase9-qualitative-qa.md](./docs/eval/phase9-qualitative-qa.md)

## OSS 関連ドキュメント

- [LICENSE](./LICENSE)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [SUPPORT.md](./SUPPORT.md)

## ライセンス

Apache License 2.0。
