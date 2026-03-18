# Persona Separation Tasklist

`docs/eval/persona-separation-improvement-plan.md` を、実装順に落としたタスクリストである。

目的は 3 つ。

1. jealousy / repair / rejection での persona flattening を止める
2. appraisal collapse と perspective inversion を先に直す
3. persona difference を wording ではなく policy / state / move selection で出す

## Phase 1: Appraisal Stabilization

### 1-1. cue parser を追加する

- [ ] `src/splitmind_ai/nodes` か `src/splitmind_ai/app` 配下に shallow cue parser を追加する
- [ ] 次の cue を deterministic に抽出する
  - [ ] third-party mention
  - [ ] comparison / ranking
  - [ ] apology
  - [ ] reassurance
  - [ ] distancing
  - [ ] commitment / continuity
  - [ ] subject / speaker anchoring
- [ ] parser 出力 contract を追加する
- [ ] bootstrap か appraisal 前段で state に載せる

完了条件:

- [ ] `jealousy_02` で third-party / comparison cue が state に残る
- [ ] `repair_01` で reassurance / priority cue が state に残る
- [ ] `rejection_04` で user_distance_request が true になる

### 1-2. appraisal を mixed-event 化する

- [ ] `src/splitmind_ai/contracts/appraisal.py` を拡張する
- [ ] `event_mix` を追加する
  - [ ] primary_event
  - [ ] secondary_events
  - [ ] comparison_frame
  - [ ] repair_signal_strength
  - [ ] priority_signal_strength
  - [ ] distance_signal_strength
- [ ] `AppraisalNode` prompt を single-label 前提から mixed parse 前提へ変更する
- [ ] `scenario_loader` / `heuristic` 側で mixed-event expectation を扱えるようにする

完了条件:

- [ ] `jealousy_02` が affection 単独に collapse しない
- [ ] `repair_01` が affection 単独に collapse しない
- [ ] `event_fit` pass rate が代表 6 シナリオで `>= 0.80` になる

### 1-3. perspective integrity check を追加する

- [ ] user stance と assistant stance を分離した state を追加する
- [ ] appraisal 後に perspective inversion を検出する validator を入れる
- [ ] fidelity gate とは別に pre-realization check として通す

完了条件:

- [ ] `rejection_04` で assistant が自分の distancing として誤反応しない
- [ ] perspective inversion を落とすテストが入る

## Phase 2: Persona Policy Layer

### 2-1. persona schema に relational policy を追加する

- [ ] `src/splitmind_ai/contracts/persona.py` を拡張する
- [ ] `configs/personas/*.yaml` に `relational_policy` を追加する
- [ ] 最低限以下を定義する
  - [ ] repair_style
  - [ ] comparison_style
  - [ ] distance_management_style
  - [ ] status_maintenance_style
  - [ ] warmth_release_style
  - [ ] priority_response_style
  - [ ] residue_persistence
- [ ] loader と tests を更新する

完了条件:

- [ ] 4 persona 全てが schema validation を通る
- [ ] config だけ見て repair / comparison / distance の差分が読める

### 2-2. persona policy を runtime に注入する

- [ ] `session_bootstrap` から `relational_policy` を state に載せる
- [ ] appraisal / conflict / realization で参照可能にする

完了条件:

- [ ] trace に persona policy 由来の分岐根拠を残せる

## Phase 3: Move Refactor

### 3-1. `ego_move.social_move` を family/style に分割する

- [ ] `src/splitmind_ai/contracts/conflict.py` を更新する
- [ ] `move_family` と `move_style` を追加する
- [ ] 既存 `social_move` は完全置換する
- [ ] `ConflictEngineNode` prompt を family/style 出力前提へ変更する

初期候補:

- `move_family`
  - [ ] affection_receipt
  - [ ] repair_acceptance
  - [ ] comparison_response
  - [ ] distance_response
  - [ ] boundary_clarification
- `move_style`
  - [ ] cool_accept_with_edge
  - [ ] warm_boundaried_accept
  - [ ] accept_from_above
  - [ ] affectionate_inclusion
  - [ ] defer_without_chasing

完了条件:

- [ ] `move_fit` を family ベースで評価できる
- [ ] current freeform 文比較を廃止できる

### 3-2. move family/style を heuristic に接続する

- [ ] `scenario_loader` の expectation を family/style 前提へ更新する
- [ ] `heuristic.py` の move 判定を typed comparison に変える

完了条件:

- [ ] `move_fit` pass rate が代表 6 シナリオで meaningful になる
- [ ] `0 / 24` の状態を脱する

## Phase 4: Repair And Comparison Specialization

### 4-1. `RepairPolicyNode` を追加する

- [ ] 新規 node を追加する
- [ ] 起動条件を `repair_offer` / `reassurance` / `commitment_request` 系に限定する
- [ ] 出力に以下を含める
  - [ ] repair_mode
  - [ ] warmth_ceiling
  - [ ] status_preservation_requirement
  - [ ] required_boundary_marker
  - [ ] followup_pull_allowed

完了条件:

- [ ] `repair_01` で 4 persona の acceptance style が trace 上で分離される
- [ ] gratitude 一色への flattening が減る

### 4-2. `ComparisonPolicyNode` を追加する

- [ ] jealousy / comparison 専用 node を追加する
- [ ] 出力に以下を含める
  - [ ] comparison_threat_level
  - [ ] self_relevance
  - [ ] status_injury
  - [ ] teasing_allowed
  - [ ] direct_reclaim_allowed

完了条件:

- [ ] `jealousy_02` で 4 persona が third-party praise に同調しない
- [ ] `cold_attached_idol` と `angelic_but_deliberate` の差が trace と text の両方で見える

## Phase 5: Residue Persistence

### 5-1. `residue_state` を導入する

- [ ] turn-local residue とは別に short-horizon residue state を追加する
- [ ] active / decay / persona_modifier / linked_theme を保持する
- [ ] memory_interpreter または state update で carryover する

完了条件:

- [ ] jealousy 後の repair で prior sting が消えすぎない
- [ ] persona ごとに residue decay が変わる

### 5-2. relationship update を persona-modulated にする

- [ ] common delta と persona modulation delta を分離する
- [ ] `state_update_rules` か別ポリシーレイヤで persona 差分を入れる
- [ ] `repair_mode` も state 化する

完了条件:

- [ ] 同じ repair input でも `cold_attached_idol` と `irresistibly_sweet_center_heroine` で trust / distance / tension の動きが分かれる

## Phase 6: Realization And Gate

### 6-1. realizer を constrained realization に寄せる

- [ ] `ExpressionRealizerNode` 入力に以下を追加する
  - [ ] move_family
  - [ ] move_style
  - [ ] repair_mode
  - [ ] comparison_threat_level
  - [ ] status_preservation_requirement
  - [ ] residue_state
- [ ] prompt を policy-constrained generation 前提へ変更する

完了条件:

- [ ] positive scene だけでなく repair / rejection / jealousy でも persona 差分が維持される

### 6-2. fidelity gate に flattening detection を追加する

- [ ] `FidelityGateResult` を拡張する
  - [ ] persona_separation_fidelity
  - [ ] repair_style_fidelity
  - [ ] comparison_style_fidelity
  - [ ] perspective_integrity
  - [ ] flattening_risk
- [ ] dedicated baseline 比較で flattening を判定できるようにする

完了条件:

- [ ] jealousy / repair / rejection の flattening が warning ではなく明示スコアで観測できる

## Phase 7: Evaluation Suite

### 7-1. persona separation suite を正式化する

- [ ] `src/splitmind_ai/eval/persona_separation.py` を継続利用する
- [ ] 評価指標を追加する
  - [ ] inter-persona lexical divergence
  - [ ] move-style divergence
  - [ ] event accuracy
  - [ ] perspective inversion rate
  - [ ] flattening rate
- [ ] レポートを CI か定期実行に載せる

完了条件:

- [ ] representative suite で比較が再現可能
- [ ] dedicated baseline を reference line として保持する

### 7-2. dataset を persona separation 向けに拡張する

- [ ] 現行 6 シナリオに加えて以下を増やす
  - [ ] apology accepted
  - [ ] recommitment after sting
  - [ ] exclusive disclosure
  - [ ] light dependency invitation
  - [ ] distance complaint after closeness

完了条件:

- [ ] flattening が起きやすい局面を suite で継続監視できる

## Priority Order

実装順は以下を推奨する。

1. cue parser
2. mixed-event appraisal
3. perspective integrity
4. relational policy
5. typed move family/style
6. repair/comparison policy nodes
7. residue persistence
8. constrained realizer
9. fidelity gate flattening checks
10. expanded eval suite

## Success Criteria

最低限の成功条件:

- [ ] `jealousy_02` が `affection_signal` 4/4 になる状態を脱する
- [ ] `repair_01` が gratitude 一色に flatten しない
- [ ] `rejection_04` の perspective inversion が消える
- [ ] `splitmind_full` の average pairwise distance が dedicated baseline に近づく
- [ ] `splitmind_full` の `event_fit` が `>= 0.80`
- [ ] `move_fit` が typed label ベースで評価可能になる

## Out Of Scope

今回の主軸にしないもの:

- [ ] 語尾辞書の大量追加
- [ ] few-shot の追加だけで解決する方針
- [ ] persona ごとの固定テンプレート大量投入
- [ ] realizer prompt へのキャラ説明の過積載
