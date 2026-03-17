# Phase 2: Runtime, Memory And UI

## 1. ゴール

このフェーズでは、MVP の「研究に使える最小実装」を成立させる。

完了ラインは以下。

1. 1ターン実行が安定する
2. relationship / mood / unresolved tensions が更新される
3. Obsidian に長期記憶が保存される
4. 研究 UI で主要 trace を観測できる

## 2. Runtime 実装

### 2.1 1ターン実行フロー

MVP の標準フローは以下。

1. `SessionBootstrapNode`
2. `InternalDynamicsNode`
3. `PersonaSupervisorNode`
4. `MemoryCommitNode`

各ノードの出力責務は重複させない。

### 2.2 InternalDynamicsNode の出力

最低限返す項目:

* `id_output`
* `ego_output`
* `superego_output`
* `defense_output`
* `dominant_desire`
* `event_flags`
* `llm_rationale_short`

`event_flags` は Python 側更新ロジックが読むため、自由文ではなく列挙型ベースに寄せる。

候補:

* `reassurance_received`
* `rejection_signal`
* `jealousy_trigger`
* `affectionate_exchange`
* `prolonged_avoidance`
* `user_praised_third_party`
* `repair_attempt`

### 2.3 PersonaSupervisorNode の出力

最低限返す項目:

* `final_response_text`
* `tone_profile`
* `leakage_level`
* `surface_intent`
* `hidden_pressure`
* `integration_rationale_short`

UI と評価の両方で使うため、説明量は短く固定する。

### 2.4 失敗時の扱い

研究用途でも fallback は必要である。

失敗ケース:

* LLM timeout
* JSON parse failure
* persona load failure
* memory write failure

対応方針:

* `InternalDynamicsNode` 失敗時は safe default bundle を生成
* `PersonaSupervisorNode` 失敗時は neutral fallback response を返す
* memory 書き込み失敗は response を潰さず warning に落とす

## 3. 状態更新エンジン

### 3.1 ルールベース更新の責務

`src/splitmind_ai/rules/state_updates.py` を作り、更新ロジックを一箇所に集約する。

入力:

* previous relationship state
* previous mood state
* `event_flags`
* latest user message
* latest final response metadata

出力:

* updated relationship state
* updated mood state
* updated unresolved tensions
* generated memory candidates

### 3.2 relationship state 初期項目

* `trust`
* `intimacy`
* `distance`
* `tension`
* `attachment_pull`

すべて 0.0 から 1.0 の範囲に正規化する。

### 3.3 mood state 初期項目

まずは単一ラベル + 強度で十分とする。

* `label`
* `intensity`
* `decay_turns_remaining`

候補ラベル:

* `calm`
* `irritated`
* `longing`
* `defensive`
* `playful`
* `withdrawn`

### 3.4 unresolved tensions

構造化項目として持つ。

必須フィールド:

* `theme`
* `intensity`
* `source`
* `created_at`
* `last_reinforced_at`

テーマ候補:

* `fear_of_replacement`
* `fear_of_rejection`
* `need_for_reassurance`
* `shame_after_exposure`

## 4. Obsidian 記憶層

### 4.1 保存対象

`docs/concept.md` の 20.3 に合わせ、保存対象は絞る。

* session summary
* emotional memory
* semantic preference memory
* relationship snapshot

### 4.1.1 source of truth

MVP では責務を以下で固定する。

* 現セッション中の `relationship state` / `mood state` / `unresolved tensions` は Python runtime state を source of truth とする
* セッションをまたぐ再開時の `relationship snapshot` / `emotional memories` / `semantic preferences` は Obsidian Vault を source of truth とする
* `SessionBootstrapNode` はセッション開始時にのみ Vault を読む
* `MemoryCommitNode` は各ターン終了時に runtime state を Vault へ反映する

したがって、1 ターンの途中で Vault を再読込して state を上書きしない。

### 4.1.2 セッション境界

MVP では、`session_id` を持つ連続対話単位を 1 セッションとみなす。

* CLI 実行では 1 回の対話実行を 1 セッションとする
* 研究 UI では、明示的な reset までを同一セッションとする
* セッション開始時に latest committed snapshot をロードする
* セッション中は Python 側 state のみ更新する
* 各ターン終了時に relationship snapshot と memory candidates を commit する
* session summary はセッション終了時、または turn 上限到達時に生成する

### 4.2 vault 内ファイル設計

`vault/` 配下に以下を作る。

```text
vault/
├── personas/
├── users/
│   └── <user_id>/
│       ├── relationship.md
│       ├── sessions/
│       ├── emotional_memories/
│       └── preferences/
└── system/
```

### 4.3 frontmatter 例

```yaml
---
type: emotional_memory
user_id: default
theme: fear_of_replacement
intensity: 0.66
tags:
  - jealousy
  - third-party
created_at: 2026-03-16T21:30:00+09:00
---
```

### 4.4 retrieval policy

1ターンで読む量は固定する。

* relationship state
* unresolved tensions 上位 3 件
* recent session summaries 3 件
* relevant emotional memories 3 件
* semantic preferences 2〜5 件

最初は frontmatter と文字列検索で十分であり、埋め込み検索は後回しにする。

### 4.5 永続化の優先順位

永続化競合が起きた場合の優先順位も固定する。

1. 現セッション中は Python runtime state を正とする
2. セッション終了後は最新 commit 済みの Vault snapshot を正とする
3. relationship snapshot は上書き保存、emotional memory と semantic preference は追記保存とする
4. commit 失敗時は runtime の応答を優先し、再試行可能な warning として trace に残す

## 5. 研究 UI

### 5.1 UI 技術選定

MVP は Streamlit を推奨する。

理由:

* Python だけで完結する
* 内部 JSON をそのまま表示しやすい
* 折りたたみ UI を最短で作れる
* 研究用ツールとして十分

### 5.2 表示対象

最低限表示する。

* chat history
* final response
* dominant desire
* selected defense mechanism
* relationship state
* mood state
* unresolved tension top 1
* raw trace JSON download

### 5.3 UI 操作項目

* persona selector
* trace mode on/off
* leakage slider
* defense frequency override
* reset session

override は本番仕様ではなく研究実験のための操作として扱う。

## 6. テスト計画

必須テスト:

* state update rules
* memory file creation
* retrieval result ordering
* Streamlit 用 service layer
* 代表シナリオの golden test

golden test の最初の対象例:

* 他者称賛による嫉妬トリガー
* reassurance による tension 回復
* 距離を取られた時の defensive 化

## 7. 完了条件

このフェーズは次を満たしたら完了とする。

1. UI から user message を送り 1ターン応答できる
2. trace が UI から確認できる
3. vault に長期記憶が保存される
4. session を跨いで relationship state を復元できる
5. 代表 3 シナリオの golden test が通る
