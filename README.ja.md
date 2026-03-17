# SplitMind-AI

[English](./README.md) | [日本語](./README.ja.md)

SplitMind-AI は、単一のペルソナプロンプトではなく、構造化された内部葛藤から応答を生成する心理力動インスパイア型 AI エージェントアーキテクチャです。

欲求、現実調停、規範圧力、防衛機制、ペルソナ統合を明示的なモジュールとして分離し、その緊張関係から最終応答を導きます。

```text
ユーザー入力
  -> 内部力動 (Id / Ego / Superego / Defense)
  -> 動機づけと社会的 appraisal
  -> Persona Supervisor
  -> Surface Realization
  -> 応答 + 状態更新 + 記憶保存
```

現在の既定 runtime は 1 ターンあたり `2` 回の LLM 呼び出しです。

## この OSS の面白さ

- 人格を「口調」ではなく「競合する内部圧力」として扱います。
- 状態、記憶、安全境界がコード上で明示されていて、観測と調整がしやすいです。
- 長期対話の質感、感情のにじみ、ためらい、矛盾を研究しやすい構造です。
- UI、評価、トレースが揃っていて、挙動を見ながら改善できます。

## 今すぐ触れるもの

- 対話と内部トレースを観測できる Streamlit 研究 UI
- relationship や drive を残す vault ベース記憶
- Pydantic schema による contract 駆動ランタイム
- ベースライン比較を含む評価フレームワーク
- 禁止パターン、出力 lint、モデレーションの 3 層安全境界

## アーキテクチャ概要

| レイヤ | 役割 |
|---|---|
| `contracts/` | LLM 入出力と内部データ交換の構造化スキーマ |
| `state/` | relationship、mood、drive、inhibition、trace の Typed state |
| `nodes/` | 力動、appraisal、arbitration、planning、realization、persistence の実行ノード |
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
git clone <repo-url>
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
- `5` つのベースライン: single-persona、persona+memory、emotion-label、flat multi-agent、full SplitMind
- `3` 層評価: contract、heuristic、人手評価

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

- Phase 8 の drive loop は state、contracts、routing、memory、safety、eval、UI まで実装済みです。
- ダッシュボードは `drive_state` を長期的な動機づけの主信号として扱います。
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

## OSS 関連ドキュメント

- [LICENSE](./LICENSE)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [SUPPORT.md](./SUPPORT.md)

## ライセンス

Apache License 2.0。
