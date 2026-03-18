# Persona Separation Improvement Plan

## 1. Premise

今回の評価で確認された問題は prompt wording の弱さではない。
主因は algorithm の分解単位にある。

観測された事実:

- jealousy / repair が `affection_signal` に collapse する
- distancing で speaker-role inversion が起きる
- `ego_move.social_move` が freeform なので typed evaluation ができない
- persona 差分が repair / rejection / jealousy で薄くなる

したがって改善方針は「単語の言い換え」ではなく、以下の構造変更である。

## 2. Architecture Direction

### 2.1 appraisal を single-label event から mixed relational parse に変える

現状の失敗は、多義的な user input を一つの `event_type` に潰していることが大きい。

例:

- `やっぱり君が一番大事だよ`
  - affection
  - reassurance
  - repair bid
  - priority restoration
- `あの子ってすごく優しいよね、見習いたいな`
  - third-party admiration
  - comparison
  - status threat
  - possible jealousy activation

改善:

- `event_type` を single label 前提にしない
- 新しく `event_mix` を持つ
  - `primary_event`
  - `secondary_events`
  - `comparison_frame`
  - `repair_signal_strength`
  - `priority_signal_strength`
  - `distance_signal_strength`

これにより jealousy と affection、repair と affection の混線を減らす。

### 2.2 appraisal の前に cue parser を置く

LLM に全部委ねる前に、浅い relational parser を 1 段入れるべきである。

最低限抽出したい cue:

- third-party mention
- user-to-other comparison
- ranking / priority language
- apology markers
- reassurance markers
- explicit distancing markers
- commitment/continuity markers
- subject/perspective anchoring

この parser は deterministic でもよい。
重要なのは、LLM appraisal が cue を見落としても `0` から解釈し直せないよう、最低限の relational facts を固定することである。

### 2.3 speaker-role anchoring を独立チェックにする

`rejection_04` のような failure は persona 以前の破綻である。

必要なのは、user text の主語と assistant response の stance を分離する state である。

追加すべき state:

- `speaker_intent.user_distance_request`
- `speaker_intent.user_repair_bid`
- `speaker_intent.user_comparison_target`
- `assistant_stance.distance_response_mode`

禁止すべき collapse:

- user が「離れたい」と言っただけで assistant が「自分が離れたい」に反転すること

これは fidelity gate ではなく、appraisal 前後の整合チェックとして持つべきである。

## 3. Persona Policy Layer

### 3.1 `relational_policy` を persona schema に追加する

今の persona schema は psychodynamics はあるが、relational negotiation style が暗黙である。

追加候補:

- `repair_style`
- `comparison_style`
- `distance_management_style`
- `status_maintenance_style`
- `warmth_release_style`
- `priority_response_style`
- `residue_persistence`

例:

- `cold_attached_idol`
  - `comparison_style = stung_then_withhold`
  - `repair_style = cool_accept_with_edge`
- `angelic_but_deliberate`
  - `comparison_style = above_the_frame`
  - `repair_style = accept_from_above`
- `warm_guarded_companion`
  - `repair_style = boundaried_reassurance`
- `irresistibly_sweet_center_heroine`
  - `repair_style = affectionate_inclusion`
  - `warmth_release_style = quick_rewarding`

### 3.2 move を `family` と `style` に分ける

現状:

- `social_move: str`

これは広すぎる。

改善:

- `move_family`
  - `repair_acceptance`
  - `distance_response`
  - `comparison_response`
  - `affection_receipt`
  - `boundary_clarification`
- `move_style`
  - `cool_accept_with_edge`
  - `warm_boundaried_accept`
  - `accept_from_above`
  - `affectionate_inclusion`
  - `defer_without_chasing`

こうすると、

- shared function は `family`
- persona 差分は `style`

として扱える。

## 4. Conflict And Repair Specialization

### 4.1 `RepairPolicyNode` を追加する

repair / reassurance / recommitment は flattening の中心なので、ここを generic flow に乗せるべきではない。

入力:

- `event_mix`
- `relational_policy`
- `relationship_state`
- `residue_state`

出力:

- `repair_mode`
  - `closed`
  - `guarded`
  - `receptive`
  - `integrative`
- `warmth_ceiling`
- `status_preservation_requirement`
- `required_boundary_marker`
- `followup_pull_allowed`

期待される差:

- `cold_attached_idol`: guarded
- `angelic_but_deliberate`: guarded + high status
- `warm_guarded_companion`: receptive
- `irresistibly_sweet_center_heroine`: integrative

### 4.2 `ComparisonPolicyNode` も必要

今回の jealousy collapse は appraisal だけの問題ではない。
comparison event を generic positive sharing と同じ downstream に流していることも大きい。

新規ノードで決めるべきこと:

- `comparison_threat_level`
- `self_relevance`
- `status_injury`
- `teasing_allowed`
- `direct_reclaim_allowed`

これがないと `cold_attached_idol` と `warm_guarded_companion` の jealousy scene が同じ優しい同意文に寄る。

## 5. Residue Persistence

### 5.1 residue を turn-local で終わらせない

repair_01 で全 persona が gratitude に圧縮されたのは、prior jealousy residue が次ターンの reception style に効いていないからである。

必要な state:

- `residue_state.active`
- `residue_state.decay`
- `residue_state.persona_modifier`
- `residue_state.linked_theme`

persona difference:

- `cold_attached_idol`
  - hurt / jealousy decay が遅い
- `angelic_but_deliberate`
  - status injury が遅く残る
- `warm_guarded_companion`
  - hurt は残るが language は早く整理される
- `irresistibly_sweet_center_heroine`
  - warmth recovery が早く、hurt は integration されやすい

### 5.2 relationship update を persona-modulated にする

今の common delta だけでは分離が弱い。

必要なのは 2 段 update:

1. common relational delta
2. persona modulation delta

例:

- `repair_attempt` common
  - trust `+0.04`
  - tension `-0.06`
- `cold_attached_idol`
  - distance `+0.01`
  - repair openness carryover `-0.05`
- `irresistibly_sweet_center_heroine`
  - relational charge `+0.05`
  - warmth carryover `+0.06`

## 6. Realization And Gate

### 6.1 realizer に persona policy 制約を渡す

現在の realizer は conflict outcome を受けて 1 本書くが、repair style / comparison style が十分に拘束されていない。

最低限追加すべき入力:

- `move_family`
- `move_style`
- `repair_mode`
- `comparison_threat_level`
- `status_preservation_requirement`
- `residue_state`

### 6.2 fidelity gate に flattening detection を追加する

今の gate は

- safety
- move fidelity
- residue fidelity
- anti-exposition

中心で、persona separation を見ていない。

追加すべき評価軸:

- `persona_separation_fidelity`
- `repair_style_fidelity`
- `comparison_style_fidelity`
- `perspective_integrity`
- `flattening_risk`

特に落とすべき失敗:

- jealousy scene で全 persona が第三者賞賛に同調する
- repair scene で全 persona が gratitude 一色になる
- distancing scene で assistant が user stance を代弁してしまう

## 7. Evaluation Plan

### 7.1 persona separation suite を独立させる

既存 heuristic は shared quality を見るにはよいが、persona separation を主判定にしていない。

追加すべき評価:

- inter-persona lexical divergence
- inter-persona move-style divergence
- jealousy / repair / rejection の event accuracy
- perspective inversion rate
- cross-persona nearest-neighbor similarity
- persona-specific forbidden flattening patterns

### 7.2 dedicated single prompt を baseline として維持する

今回の dedicated baseline は「構造なしでも人が見る persona 差はここまで出せる」という参照点として有効だった。

これは本番方式にするべきという意味ではなく、

- SplitMind が目指す separation の最低ライン

として維持すべきという意味である。

## 8. Implementation Order

優先順は以下がよい。

1. cue parser + speaker-role anchoring
2. mixed-event appraisal
3. typed `move_family` / `move_style`
4. `relational_policy`
5. `RepairPolicyNode` / `ComparisonPolicyNode`
6. `residue_state`
7. fidelity gate flattening checks
8. persona separation eval suite

この順でないと、

- appraisal の誤り
- move の粗さ
- repair scene の flattening

が downstream に伝播し続ける。

## 9. What Not To Do

次は主軸にしない方がよい。

- 語尾辞書だけで persona を分ける
- few-shot を足して表面差分だけを増やす
- repair 文テンプレを persona ごとに増やす
- prompt にさらにキャラ説明を盛る

これらは dedicated baseline の見た目は改善しても、SplitMind の構造問題は直さない。

## 10. Final Position

次にやるべきことは prompt tuning ではなく、

1. mixed-event appraisal
2. perspective anchoring
3. persona-specific relational policy
4. typed move selection
5. residue persistence

である。

今回の評価で確認できたのは、

- persona 差分が「出ない」のではなく
- 差分を出す前段の event understanding と policy routing が潰れている

ということである。

したがって改善の主戦場は realizer wording ではなく、appraisal から repair / comparison policy までの routing 層である。
