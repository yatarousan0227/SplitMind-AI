# 13. Phase 0 Baseline And Cutover Notes

## 目的

Phase 0 の役割は、実装前に

- 何を source of truth とするか
- 何を削除対象とみなすか
- どこに旧設計の依存が残っているか

を固定することにある。

このドキュメントは、Phase 1 以降で迷いなく破壊的変更を進めるための baseline である。

## Source Of Truth

次の 2 本を、新 SplitMind-AI の唯一の設計基準とする。

- [10-conflict-engine-redesign.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/10-conflict-engine-redesign.md)
- [11-persona-format-redesign.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/11-persona-format-redesign.md)

これにより、以後の実装判断では

- `voice_profile`
- `tone_guardrails`
- `weights`
- `relationship_pacing`
- `surface_state`
- `selection_critic`

を新設計へ持ち込まない。

## Cutover Principle

今回の cutover は移行ではなく置換である。

- 後方互換は持たない
- 旧 loader は延命しない
- 旧 graph は維持しない
- runtime 内で新旧両系統を並走させない

つまり、「v1 を支えながら v2 を足す」ではなく、「v1 を捨てて v2 に差し替える」。

## 現時点での主要な旧依存

### Persona v1 依存

残存箇所:

- [personas/loader.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/personas/loader.py)
- [session_bootstrap.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/session_bootstrap.py)
- [action_arbitration.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/action_arbitration.py)
- [surface_realization.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/surface_realization.py)
- [rules/safety.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/rules/safety.py)
- [eval/heuristic.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/eval/heuristic.py)
- [eval/runner.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/eval/runner.py)
- [eval/single_prompt_chat.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/eval/single_prompt_chat.py)

代表的な旧キー:

- `weights`
- `leakage_policy`
- `tone_guardrails`

### 旧 relationship 構造依存

残存箇所:

- [state/slices.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/state/slices.py)
- [state/agent_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/state/agent_state.py)
- [runtime.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/app/runtime.py)
- [session_bootstrap.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/session_bootstrap.py)
- [memory_commit.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/memory_commit.py)
- [rules/state_updates.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/rules/state_updates.py)
- [ui/app.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/ui/app.py)
- [ui/dashboard.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/ui/dashboard.py)

代表的な旧キー:

- `relationship`
- `relationship_pacing`

### 旧 surface pipeline 依存

残存箇所:

- [surface_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/surface_state.py)
- [utterance_planner.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/utterance_planner.py)
- [persona_supervisor.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/persona_supervisor.py)
- [selection_critic.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/selection_critic.py)
- [surface_realization.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/surface_realization.py)
- [app/graph.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/app/graph.py)
- [prompts/persona_supervisor.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/prompts/persona_supervisor.py)
- [ui/dashboard.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/ui/dashboard.py)
- [ui/app.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/ui/app.py)

代表的な旧概念:

- `surface_state`
- `selection_critic`
- `persona_supervisor`

## Phase 0 で決めたこと

### 1. 旧 state 名は温存しない

新設計では、

- `relationship` と `relationship_pacing`

を統合して `relationship_state` に置き換える。

### 2. 表層スタイル設定は復活させない

新設計では、

- `voice_profile`
- `tone_guardrails`
- scenario ごとの小手先ルール

を persona format に戻さない。

### 3. graph は作り直す

現行 graph の一部を温存しながら差し替えるのではなく、

- `appraisal`
- `conflict_engine`
- `expression_realizer`
- `fidelity_gate`
- `memory_commit`

中心で再構成する。

### 4. persistence は relationship history を中心に再設計する

永続化するのは `relationship_state.durable`。  
`relationship_state.ephemeral` は持ち越しても限定的とする。

## Phase 0 の実装成果

Phase 0 で完了したもの:

- 新アーキテクチャ設計の固定
- 新 persona format 設計の固定
- 実装タスクリストの作成
- cutover baseline の明文化

Phase 0 でまだ行っていないもの:

- state 定義の変更
- loader 書き換え
- graph 差し替え
- node 削除

これは未着手ではなく、Phase 1 以降へ意図的に繰り延べている。

## 次に着手するフェーズ

次は [12-next-gen-implementation-tasklist.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/12-next-gen-implementation-tasklist.md) の Phase 1。

優先順位は次の通り。

1. `state/slices.py`
2. `state/agent_state.py`
3. `contracts/*`

先に型と contract を固めないと、その後の `conflict_engine` と graph の I/O が揺れ続けるため。
