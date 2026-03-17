# Phase 1: Foundation And Contract Model

## 1. ゴール

このフェーズの目的は、概念仕様を「壊れにくい実装境界」に落とすことである。

成果物は次の 4 点。

1. 実行可能な Python プロジェクト土台
2. typed state と contract schema
3. `agent-contracts` ベースの graph 定義
4. ペルソナ定義と prompt 入出力の固定化

## 2. 主要判断

### 2.1 Python バージョン

`agent-contracts` は Python 3.11+ を前提にしているため、プロジェクトも Python 3.11 以上を固定する。

### 2.2 パッケージ構成

Poetry でも `uv` でもよいが、依存解決の速さと再現性を優先して `uv` を推奨する。
ただし、`agent-contracts` 側のサンプルや運用都合で Poetry に合わせる必要があれば後から切り替えてよい。

### 2.3 state 設計方針

`agent-contracts` の思想に合わせ、巨大な state dict を避け、意味単位の slice に分ける。

初期 slice は以下。

* `request`
* `response`
* `conversation`
* `persona`
* `relationship`
* `mood`
* `memory`
* `dynamics`
* `trace`
* `_internal`

## 3. 実装タスク

### 3.1 プロジェクト初期化

以下を追加する。

* `pyproject.toml`
* `src/splitmind_ai/__init__.py`
* `.env.example`
* `configs/agent_config.yaml`
* `README.md`

依存関係の初期候補:

* `agent-contracts`
* `langgraph`
* `langchain-core`
* `langchain-openai`
* `pydantic`
* `pyyaml`
* `python-frontmatter`
* `structlog`
* `streamlit`
* `pytest`

### 3.2 typed state の定義

`src/splitmind_ai/state/` に Pydantic model を置く。

必須 model:

* `RequestState`
* `ResponseState`
* `ConversationState`
* `RelationshipState`
* `MoodState`
* `PersonaState`
* `MemoryState`
* `DynamicsState`
* `TraceState`
* `InternalState`
* `SplitMindAgentState`

`SplitMindAgentState` は `agent-contracts` に渡す root state とし、各 slice をネスト保持する。

### 3.3 logical contract schema の定義

概念仕様 10 章を、そのまま Pydantic schema に落とす。

作成対象:

* `IdOutput`
* `EgoOutput`
* `SuperegoOutput`
* `DefenseOutput`
* `PersonaSupervisorPlan`
* `InternalDynamicsBundle`

ここで重要なのは、MVP では Id / Ego / Superego / Defense を別ノードにはしないが、出力 schema は独立に持つこと。
これにより将来の分離実装と比較実験がやりやすくなる。

### 3.4 ノード定義

`src/splitmind_ai/nodes/` に最初の 5 ノードを置く。

* `session_bootstrap.py`
* `internal_dynamics.py`
* `persona_supervisor.py`
* `memory_commit.py`
* `error_handler.py`

役割は以下。

#### SessionBootstrapNode

* セッション入力の正規化
* persona 読み込み
* 既存 memory / relationship state のロード
* request slice 生成

#### InternalDynamicsNode

* Call 1 を担当
* Id / Ego / Superego / Defense 候補を一括で JSON 生成
* dominant desire と event flags を返す

#### PersonaSupervisorNode

* Call 2 を担当
* `InternalDynamicsBundle` と persona から最終応答を単一生成
* trace 用の統合理由も返す

#### MemoryCommitNode

* LLM 非依存
* relationship state / mood state / unresolved tensions をルール更新
* Obsidian 保存対象を生成

#### ErrorNode

* contract violation や LLM parse failure の集約
* response slice を安全に終端させる

### 3.5 NodeContract 設計

各ノードで最低限宣言する。

* `name`
* `description`
* `reads`
* `writes`
* `supervisor`
* `trigger_conditions`
* `is_terminal`

想定 supervisor は最初は 1 つでよい。

* `main`

MVP では複雑な supervisor hierarchy を持ち込まない。
複数 supervisor は Phase 3 以降に再検討する。

#### 3.5.1 MVP の read / write 行列

MVP 実装では、各 runtime node の責務境界を以下で固定する。

| Node | Reads | Writes | Trigger |
| --- | --- | --- | --- |
| `SessionBootstrapNode` | external input, persona config, latest committed vault snapshot | `request`, `conversation`, `persona`, `relationship`, `mood`, `memory`, `_internal.session` | turn start |
| `InternalDynamicsNode` | `request`, `conversation`, `persona`, `relationship`, `mood`, `memory`, `_internal.session` | `dynamics`, `trace.internal_dynamics`, `_internal.event_flags` | `request.user_message` が存在する |
| `PersonaSupervisorNode` | `request`, `persona`, `relationship`, `mood`, `dynamics`, `memory`, `_internal.event_flags` | `response`, `trace.supervisor` | `dynamics` が validation 済み |
| `MemoryCommitNode` | `request`, `response`, `relationship`, `mood`, `memory`, `dynamics`, `_internal.event_flags`, `_internal.session` | `relationship`, `mood`, `memory`, `trace.memory_commit`, `_internal.persistence` | `response.final_response_text` が存在する |
| `ErrorNode` | `_internal.errors`, `request`, `dynamics`, `response` | `response`, `trace.error`, `_internal.status` | contract violation または node failure 発生時 |

補足:

* `relationship` / `mood` / `memory` は `SessionBootstrapNode` でロードし、`MemoryCommitNode` だけが永続更新してよい。
* `InternalDynamicsNode` は final response を書かない。
* `PersonaSupervisorNode` は状態更新を行わない。
* `ErrorNode` は通常系では実行されず、response を安全終端させる専用ノードとする。

### 3.6 graph builder と registry

`src/splitmind_ai/app/graph.py` で registry 登録と graph build を一元化する。

必須処理:

* ノード登録
* config 読み込み
* graph build
* entry point 設定
* 実行用 facade 提供

CLI からも同じ registry を参照できるようにする。

### 3.7 persona 定義

`configs/personas/` に YAML を置く。

最低 2 ペルソナを用意する。

* `cold_attached_idol.yaml`
* `warm_guarded_companion.yaml`

含める項目:

* base attributes
* weight parameters
* default defense biases
* leakage policy
* tone guardrails
* prohibited expressions

### 3.8 prompt 設計

`src/splitmind_ai/prompts/` に prompt builder を置く。

初期方針:

* prompt テンプレートは Python 文字列または Jinja2 のどちらかに統一
* 出力 JSON schema は code 側で source of truth を持つ
* prompt 側で schema の重複定義をしない

特に `InternalDynamicsNode` では JSON parse failure を避けるため、自由文を抑えた schema-first prompt を採用する。

## 4. 推奨コード配置

```text
src/splitmind_ai/
├── app/
│   ├── graph.py
│   ├── runtime.py
│   └── settings.py
├── contracts/
│   ├── dynamics.py
│   ├── persona.py
│   └── memory.py
├── nodes/
├── personas/
├── prompts/
└── state/
```

## 5. テスト計画

Phase 1 では LLM 品質ではなく「境界が壊れないこと」を検証する。

必須テスト:

* state model validation
* contract reads / writes 整合性
* graph build 成功
* persona YAML の読み込み
* internal dynamics JSON parse
* error fallback

`agent-contracts validate` と `agent-contracts visualize` を CI に入れる前提で進める。

## 6. 完了条件

このフェーズは次を満たしたら完了とする。

1. `python -m splitmind_ai.app.runtime` で 1 ターン実行できる
2. `InternalDynamicsNode` の構造化出力が schema validation を通る
3. `PersonaSupervisorNode` が final response を返せる
4. graph visualization を生成できる
5. 主要 persona を設定ファイルで切り替えられる

## 7. この段階で意図的にやらないこと

* UI 実装
* Obsidian 永続化の本実装
* ベースライン bot 比較
* 複雑な評価指標
