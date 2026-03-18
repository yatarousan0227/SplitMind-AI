# 12. Next-Gen Implementation Tasklist

## 前提

このタスクリストは、次の 2 本を実装上の唯一の設計ソースとして扱う。

- [10-conflict-engine-redesign.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/10-conflict-engine-redesign.md)
- [11-persona-format-redesign.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/11-persona-format-redesign.md)

この改修では、次を前提にする。

- 後方互換は不要
- 旧 persona format の互換 loader は作らない
- 旧 graph 構成は保持しない
- 検証スクリプトの整備は一旦スコープ外

つまり、`v1 を抱えたまま v2 を足す` のではなく、`現行実装を新アーキテクチャへ置き換える` 計画である。

## 成果物

今回の改修で最終的に揃うべきものは次の 7 つ。

1. 新 persona schema
2. 新 relationship state schema
3. 新 graph
4. `conflict_engine`
5. `expression_realizer`
6. `fidelity_gate`
7. 新 persistence 経路

## フェーズ 0: 実装方針の固定

### 0-1. 旧アーキテクチャの凍結

Status: Done
Note: loader と persona source は切替済み。下流ノードの旧参照削除は後続フェーズで行う

- [10-conflict-engine-redesign.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/10-conflict-engine-redesign.md) と [11-persona-format-redesign.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/11-persona-format-redesign.md) を実装基準として固定する
- 旧 `weights / tone_guardrails / leakage_policy` は以後設計判断に使わない
- `relationship` と `relationship_pacing` を別 slice として維持する案を捨てる

### 0-2. 削除対象の明文化

Status: Done

削除または吸収対象:

- [surface_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/surface_state.py)
- [selection_critic.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/selection_critic.py)
- 旧 `surface_realization` 相当ノード
- 旧 `utterance_planner`
- 旧 `persona_supervisor`
- 旧 `relationship` / `relationship_pacing` 二重管理

統合吸収対象:

- [action_arbitration.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/action_arbitration.py) の社会行動決定
- [motivational_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/motivational_state.py) の drive 集約ロジック

成果物:

- [13-phase-0-baseline-and-cutover-notes.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/13-phase-0-baseline-and-cutover-notes.md)

## フェーズ 1: 新 state / contract の定義

### 1-1. state slices 再設計

Status: Done

対象:

- [slices.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/state/slices.py)
- [agent_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/state/agent_state.py)

タスク:

- `PersonaSlice` を新 schema に置換
- `RelationshipSlice` と `RelationshipPacingSlice` を廃止
- `relationship_state` を `durable / ephemeral` 付きで新設
- `conflict_state` slice を新設
- `appraisal` の必要最小 contract を再定義
- `response` と `trace` で新ノード群の出力を受けられるようにする

完了条件:

- 型定義上、旧 persona / relationship 構造への参照が消える

### 1-2. contract モデル再定義

Status: Done

対象候補:

- [src/splitmind_ai/contracts](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/contracts)

タスク:

- `appraisal` contract を新アーキテクチャ準拠へ整理
- `conflict_engine` 用 contract を追加
- `fidelity_gate` 判定 contract を追加
- memory commit 用の `conflict summary` contract を追加

完了条件:

- 各ノードが natural language ではなく構造化出力で接続できる

## フェーズ 2: persona system 全面置換

### 2-1. persona schema 実装

Status: Done

対象:

- [loader.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/personas/loader.py)
- persona config 群

タスク:

- `persona_version: 2` 前提の loader を実装
- 旧 schema 用の分岐を削除
- loader 出力を `NormalizedPersonaProfile` 相当の構造に統一

完了条件:

- loader と persona source of truth が新 schema になる

### 2-2. 既存 persona の移植

Status: Done
Note: config 移植は完了。runtime での全面消化は後続フェーズ

対象:

- [configs/personas](/Users/iwasakishinya/Documents/hook/SplitMind-AI/configs/personas)

タスク:

- 既存 persona を全件、新 schema へ移植
- 各 persona に `psychodynamics`, `relational_profile`, `defense_organization`, `ego_organization`, `safety_boundary` を定義
- voice 指定や scenario 直書きが残っていないか確認

完了条件:

- 旧 persona YAML が repo から消えるか、少なくとも runtime から参照されない

## フェーズ 3: relationship persistence 再設計

### 3-1. persistent relationship model 実装

Status: Done

対象:

- [vault_store.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/memory/vault_store.py)
- [session_bootstrap.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/session_bootstrap.py)
- [memory_commit.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/memory_commit.py)

タスク:

- vault 上の relationship 保存形式を `relationship_state.durable` 前提に置換
- session start で durable state を読み込み、ephemeral state を初期化
- turn end で durable state のみ永続化
- unresolved tension を summary 形式へ整理

完了条件:

- セッションをまたいで durable relationship state が復元される
- ephemeral state はセッション開始時に再初期化される

### 3-2. 旧 relationship ロジックの整理

Status: Done

対象:

- [state_updates.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/rules/state_updates.py)

タスク:

- `relationship` と `relationship_pacing` の二重更新を廃止
- 新 `relationship_state` を更新する関数へ再編
- event flags 前提の更新から、`appraisal + ego_move + residue` 前提へ寄せる

完了条件:

- relationship update の source of truth が 1 系統になる

## フェーズ 4: graph 再構築

### 4-1. 新ノード実装

Status: Done

対象:

- [src/splitmind_ai/nodes](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes)

追加するノード:

- `appraisal`
- `conflict_engine`
- `expression_realizer`
- `fidelity_gate`
- `memory_commit`

タスク:

- `appraisal` を relational event 抽出へ簡素化
- `conflict_engine` で `id_impulse / superego_pressure / ego_move / residue / expression_envelope` を生成
- `expression_realizer` で 1 本だけ生成
- `fidelity_gate` で `move_fidelity / residue_fidelity / structural_persona_fidelity / hard_safety` を検査
- `memory_commit` を新 state 前提に書き換え

完了条件:

- 1 ターンが新 graph だけで完結する

### 4-2. 旧ノード撤去

Status: Done
Note: graph / registry / trigger 経路からは除去済み。ファイルの物理削除は repository cleanup フェーズで実施

削除対象:

- [surface_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/surface_state.py)
- [selection_critic.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/selection_critic.py)
- 旧 planner 系ノード

吸収対象:

- [action_arbitration.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/action_arbitration.py) の行動決定ロジック
- [motivational_state.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/motivational_state.py) の persistent drive ロジック

完了条件:

- graph 定義から旧ノード名が消える

### 4-3. graph wiring 更新

Status: Done

対象:

- [graph.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/app/graph.py)

タスク:

- graph を新ノード列へ差し替え
- dependency injection を新 contract に合わせる
- 旧 supervisor / old node dependencies を削除

完了条件:

- app runtime が新 graph を起動できる

## フェーズ 5: prompt / realization 層の整理

### 5-1. prompt 群の全面整理

Status: Done
Note: next-gen prompt builders を追加し、expression_realizer / fidelity_gate は LLM 利用時のみ構造化 prompt を使い、未接続時は deterministic fallback を維持

対象候補:

- [src/splitmind_ai/prompts](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/prompts)

タスク:

- `persona_supervisor` 依存を削除
- `voice_profile` 前提の prompt を削除
- `appraisal`, `conflict_engine`, `expression_realizer`, `fidelity_gate` 用 prompt を再定義
- prompt が persona の構造パラメータだけを参照するよう統一

完了条件:

- 「どう喋るか」の直接指定が prompt から消える

## フェーズ 6: runtime / UI / trace の更新

### 6-1. runtime 更新

Status: Done

対象:

- [runtime.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/app/runtime.py)

タスク:

- carry-forward 対象 slice を新 schema に合わせる
- 旧 `relationship`, `relationship_pacing`, `surface_state` 参照を削除
- `conflict_state` と新 `relationship_state` を turn 間で保持する

完了条件:

- multi-turn runtime が新 state で継続する

### 6-2. dashboard / UI 更新

Status: Done

対象:

- [ui/app.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/ui/app.py)
- [ui/dashboard.py](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/ui/dashboard.py)

タスク:

- dashboard 表示を `relationship_state.durable / ephemeral` に置換
- `conflict_state` の可視化を追加
- 旧 `relationship_pacing`, `selection_critic`, `surface_state` 前提の表示を削除

完了条件:

- UI から旧概念が消える

### 6-3. trace / logging 更新

Status: Done

対象:

- trace 出力周辺
- logging utils

タスク:

- trace を `appraisal`, `conflict_engine`, `expression_realizer`, `fidelity_gate`, `memory_commit` 単位に整理
- `selection_critic` 由来の trace 表現を削除

完了条件:

- trace が新因果構造をそのまま読める

## フェーズ 7: repository cleanup

### 7-1. 旧概念の掃除

Status: Done
Note: active runtime / UI / prompts / node tests から旧概念は削除済み。eval 下の旧比較ロジックはもともとスコープ外なので残置

タスク:

- 未使用の slice, contract, prompt, helper を削除
- README や docs から旧 pipeline 名称を除去
- dead code を残さない

完了条件:

- `surface_state`, `selection_critic`, `voice_profile`, `tone_guardrails` などの旧設計語がランタイム実装から消える

## 実装順序

推奨順は次の通り。

1. state / contract
2. persona system
3. relationship persistence
4. graph / nodes
5. prompts
6. runtime / UI
7. cleanup

この順にする理由は、先に state と persona を固定しないと、`conflict_engine` の I/O と graph wiring が安定しないため。

## マイルストーン

### M1. 型が決まる

- state / contract が新設計で固定される

### M2. persona が差し替わる

- 旧 persona format が runtime から消える

### M3. relationship が永続化される

- durable relationship state の保存と復元が動く

### M4. 新 graph が立つ

- 旧 pipeline を通らず 1 ターン完走できる

### M5. 旧設計が消える

- runtime から旧 node / prompt / slice が消える

## スコープ外

今回あえて外すもの:

- 比較評価スクリプトの整備
- 自動ベンチマーク拡充
- v1 互換 layer
- 段階的 migration tooling

必要なら次に、このタスクリストを issue 単位まで分解して、`1 issue = 1 PR` の粒度に落とします。
