# Phase 4: Vault Memory Redesign

## 1. ゴール

Phase 2 で実装した Vault 保存層の実態調査により、以下が判明した。

* セッション要約が一度も書き込まれていない
* ムード状態がセッション跨ぎで毎回リセットされる
* セマンティック嗜好の生成ロジックが未実装
* 感情記憶の保存内容が粗く、追跡・再利用に耐えない
* `user_sensitivities` が常に空

このフェーズでは「保存戦略の再設計と完全実装」を行い、セッションをまたいだ記憶の連続性を実現する。

---

## 2. 現状の問題点マップ

| 項目 | VaultStore メソッド | 実際に保存されるか | 問題の根本 |
|------|--------------------|--------------------|-----------|
| 関係値スナップショット | `save_relationship` | ✅ 毎ターン | 問題なし |
| セッション要約 | `save_session_summary` | ❌ 呼出元なし | `MemoryCommitNode` / `run_session` が呼ばない |
| 感情記憶 | `save_emotional_memory` | ⚠️ 条件付き | `emotion` に `dominant_desire` を流用、内容が粗い |
| セマンティック嗜好 | `save_semantic_preference` | ❌ 候補が常に空 | `generate_memory_candidates` に生成ロジックがない |
| ムード | なし | ❌ メソッド自体なし | Vault に保存・ロードの仕組みがない |
| ユーザー感応性 | なし | ❌ 書込みなし | 抽出ロジックが未実装 |

---

## 3. 設計方針

### 3.1 保存タイミングの再整理

```
ターン終了時（毎回）
  ├── 関係値スナップショット     ← 現状どおり
  ├── ムードスナップショット      ← 新規追加
  └── 感情記憶（閾値超え時）     ← 品質改善

セッション終了時（1回）
  ├── セッション要約             ← 新規追加
  ├── セマンティック嗜好         ← 新規追加
  └── ユーザー感応性の更新       ← 新規追加
```

### 3.2 感情記憶と動的欲求の分離

現状は `emotion` フィールドに `dominant_desire`（Id の欲求）を流用している。
これは概念的に正しくない。以下のように分離する。

```
emotional_memory.emotion     = AI が感じた感情ラベル（longing / irritation / warmth 等）
emotional_memory.trigger     = その感情を引き起こした dominant_desire
emotional_memory.user_text   = ユーザー発話（先頭 300 文字）
emotional_memory.agent_text  = AI 応答（先頭 300 文字）
emotional_memory.session_id  = 追跡用
emotional_memory.turn_number = 追跡用
```

### 3.3 セッション要約の生成戦略

LLM で要約を生成するか、ルールベースで要約するかを選択できる設計にする。
MVP では以下のルールベース要約を採用する。

```
セッション要約に含める情報:
  - セッションの会話ターン数
  - 最終ムード
  - 発火したイベントフラグの一覧
  - 関係値の変化量（開始時との差分）
  - 感情記憶として保存したエントリの件数
  - 会話の最初と最後のユーザー発話（各先頭 100 文字）
```

オプションとして LLM 要約（設定で切替可能）も後から差し込める拡張ポイントを残す。

### 3.4 セマンティック嗜好の抽出ルール

ルールベースで以下のトリガーを設ける。

| トリガー条件 | 抽出する嗜好 |
|-------------|-------------|
| `affectionate_exchange` が発火 | ユーザーが好む話題・トーン |
| ユーザー発話に固有名詞（アニメ・音楽等）が含まれる | 趣味・関心分野 |
| 同一テーマが 2 セッション以上で登場 | 長期関心 |

MVP では「固有名詞検出なし」のシンプル版として、イベントフラグ発火時に現在のターン話題を嗜好候補として記録する。

---

## 4. 実装タスク

### Task 4-1: `VaultStore` にムード保存を追加

**対象ファイル**: `src/splitmind_ai/memory/vault_store.py`

追加するメソッド:
- `save_mood(user_id, mood: dict)` — `mood.md` に上書き保存
- `load_mood(user_id)` — `mood.md` から読み込み

保存先: `vault/users/<user_id>/mood.md`

```yaml
# フロントマター例
---
type: mood_snapshot
user_id: default
base_mood: withdrawn
irritation: 0.3
longing: 0.5
protectiveness: 0.0
fatigue: 0.1
openness: 0.4
turns_since_shift: 2
updated_at: "2026-03-17T10:00:00"
---
```

---

### Task 4-2: `VaultStore.commit_turn` にムード保存を追加

**対象ファイル**: `src/splitmind_ai/memory/vault_store.py`

`commit_turn()` のシグネチャを拡張する。

```python
def commit_turn(
    self,
    user_id: str,
    relationship: dict,
    mood: dict,                      # 新規追加
    memory_candidates: dict,
) -> None:
```

内部で `save_mood(user_id, mood)` を呼ぶ。

---

### Task 4-3: `SessionBootstrapNode` でムードをVaultからロード

**対象ファイル**: `src/splitmind_ai/nodes/session_bootstrap.py`

```python
# 現状（常にデフォルト）
mood = dict(_DEFAULT_MOOD)

# 変更後
vault_mood = self._vault.load_mood(user_id) if self._vault else None
mood = vault_mood if vault_mood else dict(_DEFAULT_MOOD)
```

---

### Task 4-4: `MemoryCommitNode` からムードをVaultへ渡す

**対象ファイル**: `src/splitmind_ai/nodes/memory_commit.py`

`commit_turn` 呼び出しに `mood=updated_mood` を追加。

---

### Task 4-5: 感情記憶スキーマの改善

**対象ファイル**: `src/splitmind_ai/rules/state_updates.py`

`generate_memory_candidates` の感情記憶エントリを以下に変更する。

```python
{
    "event": user_message[:300],          # 現状 200 → 300
    "agent_response": final_response[:300], # 現状 100 → 300
    "emotion": _map_desire_to_emotion(dominant),  # 新規: 欲求→感情マッピング
    "trigger": dominant,                   # 新規: 欲求を trigger として保持
    "intensity": affective,
    "session_id": session_id,             # 新規
    "turn_number": turn_number,           # 新規
    "created_at": now,
}
```

`_map_desire_to_emotion` は欲求ラベルを感情ラベルへ変換する小さな辞書関数として実装する。

```python
_DESIRE_TO_EMOTION = {
    "fear_of_replacement": "longing",
    "need_for_reassurance": "longing",
    "fear_of_rejection": "anxiety",
    "shame_after_exposure": "shame",
    # 未マッピングはそのまま返す
}
```

---

### Task 4-6: セマンティック嗜好の生成ロジック実装

**対象ファイル**: `src/splitmind_ai/rules/state_updates.py`

`generate_memory_candidates` の `semantic_preferences` 生成を実装する。

```python
# affectionate_exchange が発火した場合、話題を嗜好として記録
if event_flags.get("affectionate_exchange") and user_message:
    candidates["semantic_preferences"].append({
        "topic": "affectionate_context",
        "preference": user_message[:150],
        "confidence": 0.6,
        "created_at": now,
    })
```

MVP 版は粗くてよい。セッション要約と組み合わせて精度を上げるのは後続フェーズで行う。

---

### Task 4-7: セッション終了時の要約保存

**対象ファイル**: `src/splitmind_ai/app/runtime.py`

`run_session()` のメインループ終了後（`break` の直前）に要約保存を追加する。

```python
# セッション終了時
if messages and vault_store is not None:
    summary = _build_session_summary(
        messages=messages,
        turn_count=turn_count,
        initial_state=initial_vault_state,
        final_state=latest_state,
        event_log=session_event_log,
    )
    vault_store.save_session_summary(
        user_id=user_id,
        session_id=session_id,
        summary=summary["text"],
        turn_count=turn_count,
        dominant_mood=latest_state.get("mood", {}).get("base_mood", "calm"),
        key_events=summary["key_events"],
    )
```

`_build_session_summary` はルールベースで以下を生成する関数。

```
入力:
  - messages: 全ターンの会話リスト
  - turn_count: ターン数
  - initial_state / final_state: 関係値の差分計算用
  - event_log: セッション中に発火したイベントフラグの累積

出力テキスト例:
  "3ターンの会話。ユーザーは他者を褒める発言をし（jealousy_trigger）、
   最終的に関係修復の試みがあった（repair_attempt）。
   信頼度: 0.50 → 0.53。最終ムード: withdrawn。"
```

---

### Task 4-8: セッション中のイベントフラグ累積

**対象ファイル**: `src/splitmind_ai/app/runtime.py`

現状、`event_flags` は各ターンの `_internal` にあるが、セッション全体での累積が取れていない。

```python
# run_session() 内
session_event_log: list[dict] = []   # 新規追加

# ターン終了後
turn_events = result.get("_internal", {}).get("event_flags", {})
fired = [k for k, v in turn_events.items() if v]
if fired:
    session_event_log.append({"turn": turn_count, "events": fired})
```

これをセッション要約生成（Task 4-7）に渡す。

---

### Task 4-9: `VaultStore.commit_turn` のシグネチャ変更に合わせたテスト更新

**対象ファイル**: `tests/unit/test_vault_store.py`、`tests/unit/test_nodes.py`

- `commit_turn` の `mood` 引数追加に対応
- `save_mood` / `load_mood` の単体テストを追加
- セッション要約の保存・ロードテストを追加

---

## 5. 実装順序

依存関係を考慮した推奨順序。

```
Task 4-1  VaultStore: save_mood / load_mood 追加
Task 4-2  VaultStore: commit_turn シグネチャ拡張
Task 4-3  SessionBootstrapNode: ムードロード対応
Task 4-4  MemoryCommitNode: ムード渡し対応
  ↓
Task 4-5  感情記憶スキーマ改善 (state_updates.py)
Task 4-6  セマンティック嗜好の生成ロジック (state_updates.py)
  ↓
Task 4-8  イベントフラグ累積 (runtime.py)
Task 4-7  セッション終了時の要約保存 (runtime.py)
  ↓
Task 4-9  テスト更新
```

---

## 6. 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `src/splitmind_ai/memory/vault_store.py` | 変更 | `save_mood`/`load_mood` 追加、`commit_turn` 拡張 |
| `src/splitmind_ai/nodes/session_bootstrap.py` | 変更 | ムードをVaultからロード |
| `src/splitmind_ai/nodes/memory_commit.py` | 変更 | ムードを `commit_turn` へ渡す |
| `src/splitmind_ai/rules/state_updates.py` | 変更 | 感情記憶スキーマ改善、嗜好生成追加、`_map_desire_to_emotion` 追加 |
| `src/splitmind_ai/app/runtime.py` | 変更 | イベントフラグ累積、セッション終了時の要約保存 |
| `tests/unit/test_vault_store.py` | 変更 | `save_mood`/`load_mood` テスト、要約テスト追加 |
| `tests/unit/test_nodes.py` | 変更 | `commit_turn` シグネチャ変更対応 |
| `tests/unit/test_state_updates.py` | 変更 | 感情記憶スキーマ・嗜好生成のテスト更新 |

---

## 7. 完了基準

以下がすべて満たされたとき、Phase 4 完了とする。

1. セッション終了後に `vault/users/<user_id>/sessions/<session_id>.md` が生成される
2. 次セッション開始時にムードが前回の最終値から始まる（デフォルト値でない）
3. `affectionate_exchange` 発火時にセマンティック嗜好が `preferences/` に書き込まれる
4. 感情記憶に `agent_response`・`trigger`・`session_id`・`turn_number` が含まれる
5. すべての既存テストが引き続きパスする
6. 新規テストが `pytest tests/unit/` でパスする

---

## 8. 将来拡張（Phase 5 候補）

このフェーズでは見送るが、次フェーズの候補として記録しておく。

* **LLM 要約**: ルールベース要約から LLM 生成要約への切替オプション
* **user_sensitivities の自動抽出**: ユーザー発話パターンから感応テーマを抽出
* **会話ターン全文保存**: セッション単位で全発話ペアを Vault に記録
* **ベクトル検索**: 感情記憶・嗜好の類似検索（Vault から埋め込み DB への移行）
* **会話履歴のコンテキスト拡張**: 直近 6 件制限の緩和（要約+重要ターン混合）
