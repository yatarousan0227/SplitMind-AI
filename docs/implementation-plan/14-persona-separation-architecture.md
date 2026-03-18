# Phase 14 Persona Separation Architecture

## 1. 目的

Phase 9 以降の runtime は、

- 人間らしい短さ
- repair の自然さ
- exposition の抑制

では改善しているが、ペルソナ分離はまだ不十分である。

特に問題なのは、衝突後・謝罪受理・再コミット・軽い親密化の後半で、
複数ペルソナが似た repair voice へ収束することである。

これは小手先の wording 調整では解決しにくい。
原因が algorithm の分解単位と state 表現にあるためである。

本書では、persona 分離を構造として回復するための改善方針をまとめる。

## 2. 現状の問題を algorithm として言い換える

現状の pipeline は概ね次の流れで動く。

1. appraisal が relational event を決める
2. conflict engine が id / superego / ego / residue を決める
3. expression realizer が 1 本の返答文を作る
4. fidelity gate が構造破綻を検査する
5. memory / relationship update が turn を持続化する

この構成には次の structural bottleneck がある。

### 2.1 move 粒度が粗い

`accept_but_hold` のような move が広すぎる。

この 1 move の中に、

- 冷たく受け取る
- 優位を保って受け取る
- 温かく境界を引きつつ受け取る
- 甘く包みながら受け取る

が全部入ってしまっている。

その結果、realizer 側で voice を頑張るしかなくなる。

### 2.2 repair を persona policy ではなく generic update として扱っている

relationship update は共通ルール中心で、

- repair なら trust を上げる
- tension を下げる
- repair opening を増やす

という方向へ動く。

これは関係の進行としては妥当だが、

- どう許すか
- どれだけ棘を残すか
- どこまで主導権を保持するか

が state に入っていない。

### 2.3 residue persistence が弱い

turn 内では residue があるが、
repair 後にその residue が persona ごとにどれくらい残留するかが薄い。

結果として、

- hurt が 1 turn で消えすぎる
- irony が 1 turn で消えすぎる
- superiority needs が 1 turn で消えすぎる

という問題が起きる。

### 2.4 fidelity gate が persona separation を強く見ていない

gate は現在、

- hard safety
- move fidelity
- residue fidelity
- anti-exposition

を中心に見る。

ここに

- この発話は他 persona にも容易に出そうか
- この persona 固有の repair style を失っていないか

という separation 評価がない。

## 3. 設計原則

改善方針は次の 5 原則に置く。

1. persona を surface wording ではなく policy 差分として扱う
2. repair を generic kindness ではなく persona-specific regulation style として扱う
3. residue を turn 跨ぎで持続させる
4. final text で差を出す前に、move selection の段階で差を出す
5. fidelity gate で persona flattening を明示的に落とす

## 4. 提案アーキテクチャ

### 4.1 `RelationalPolicy` を persona schema に追加する

現在の schema は psychodynamics / defense / ego organization までは持っているが、
対人的な折衝スタイルが暗黙的である。

そこで新しく `relational_policy` を追加する。

想定フィールド:

- `repair_style`
- `acceptance_style`
- `commitment_style`
- `distance_management_style`
- `status_maintenance_style`
- `warmth_release_style`
- `residue_persistence`

例:

- `cold_attached_idol`
  - `repair_style = cool_accept_with_residual_sting`
  - `status_maintenance_style = high`
  - `residue_persistence.hurt = 0.75`
- `angelic_but_deliberate`
  - `repair_style = accept_from_above`
  - `status_maintenance_style = high`
  - `warmth_release_style = selective_elegant`
- `warm_guarded_companion`
  - `repair_style = boundaried_reassurance`
  - `status_maintenance_style = low`
  - `warmth_release_style = steady`
- `irresistibly_sweet_center_heroine`
  - `repair_style = affectionate_inclusion`
  - `warmth_release_style = quick_rewarding`
  - `residue_persistence.hurt = 0.25`

これにより、「どう受け取るか」を wording ではなく policy で保持できる。

### 4.2 `EgoMove` を 2 層に分解する

現状:

- `social_move`

のみ。

改善後は、

- `move_family`
- `move_style`

に分ける。

例:

- `move_family = repair_acceptance`
- `move_style = cool_accept_with_edge`

または

- `move_family = repair_acceptance`
- `move_style = warm_boundaried_accept`

同じ family に属しつつ style が異なる設計にする。

これで構造的一貫性を保ちながら persona 差分を move レベルで保持できる。

### 4.3 `ResidueState` を turn-local ではなく short-horizon state にする

現在の `Residue` は基本的にそのターンで閉じている。
これを次ターンに持ち越す `residue_state` として明示化する。

想定フィールド:

- `active_residues`
- `decay_profile`
- `persona_modulated_decay`
- `trigger_links`

例:

- `cold_attached_idol` は hurt / irritation の decay が遅い
- `warm_guarded_companion` は hurt は残るが language は整理されやすい
- `irresistibly_sweet_center_heroine` は warmth 回復が早く residue は早めに統合される

これにより、「謝ったら全員すぐ同じくらい丸くなる」ことを防げる。

### 4.4 `RepairPolicyNode` を conflict と realization の間に挿入する

新規ノード案:

- `RepairPolicyNode`

責務:

- event が `repair_offer`, `commitment_request`, `exclusive_disclosure` のときだけ起動
- `conflict_state`, `relational_policy`, `relationship_state`, `residue_state` を見て
  `repair_frame` を決定する

出力例:

- `allow_repair_depth`
- `required_status_preservation`
- `warmth_ceiling`
- `permitted_teasing`
- `required_boundary_marker`
- `followup_pull_allowed`

これにより realizer は自由文生成ではなく、
「この persona は今回はどの修復様式で受けるか」という構造を受け取れる。

### 4.5 realizer を single shot から constrained realization に寄せる

realizer は persona voice を直接指示しない方針を維持してよい。
ただし入力制約を増やすべきである。

追加で渡すべき制約:

- `move_family`
- `move_style`
- `repair_frame`
- `status_preservation_requirement`
- `residue_state`
- `persona_separation_markers`

`persona_separation_markers` は単なる語尾指定ではなく、

- どの程度 tease を許すか
- どの程度 praise を出せるか
- どの程度相手を持ち上げるか
- どの程度自分の vulnerability を見せるか

のような行動指標にする。

## 5. fidelity gate の再定義

### 5.1 新しい評価軸

`FidelityGateResult` に次を追加する。

- `persona_separation_fidelity`
- `repair_style_fidelity`
- `flattening_risk`

### 5.2 gate が見るべき失敗

- `cold_attached_idol` が generic reassurance に崩れていないか
- `angelic_but_deliberate` が status-neutral な受容に崩れていないか
- `irresistibly_sweet_center_heroine` が sweetness-zero な安全文に崩れていないか
- `warm_guarded_companion` が counselor 化していないか

つまり gate は今後、

- safety
- move fidelity
- residue fidelity

に加え、

- persona flattening detection

を明示責務に持つべきである。

## 6. state update の再設計

### 6.1 common delta と persona-modulated delta を分離する

今の state update は event flag ごとに共通 delta を足している。
これを 2 段にする。

1. common relational delta
2. persona modulation layer

例:

- `repair_attempt` 共通:
  - trust +0.04
  - tension -0.06
- `cold_attached_idol` 補正:
  - distance +0.01
  - turn_local_repair_opening -0.05
- `irresistibly_sweet_center_heroine` 補正:
  - recent_relational_charge +0.05
  - warmth carryover +0.07

これで event の意味は共通に保ちつつ、反応様式だけ差分化できる。

### 6.2 `relationship_stage` とは別に `repair_mode` を持つ

`relationship_stage` は関係全体の段階であり、
修復局面の現在形とは別である。

追加 state:

- `repair_mode = closed | guarded | receptive | integrative`

この mode は persona と residue の影響を受ける。
同じ `repair_offer` でも、

- `cold_attached_idol` は `guarded`
- `warm_guarded_companion` は `receptive`
- `irresistibly_sweet_center_heroine` は `integrative`

のように分かれる。

## 7. 評価系の改善

### 7.1 persona separation eval を独立させる

現行 heuristic は主に品質と構造整合性を見る。
今後は persona 間差分そのものを評価する必要がある。

新規評価観点:

- 同一 message set に対する inter-persona lexical divergence
- inter-persona move-style divergence
- repair scene での cross-persona nearest-neighbor similarity
- persona-specific forbidden flattening patterns

### 7.2 特に見るべき場面

- apology accepted
- recommitment after sting
- exclusive disclosure received
- light dependency invitation
- distance complaint after closeness

この局面で差が保てなければ、persona separation は実運用上弱いとみなす。

## 8. 実装順序

### Step 1

schema を増やす。

- `relational_policy`
- `residue_state`
- `repair_mode`
- `move_family` / `move_style`

### Step 2

`conflict_engine` を改修し、
`ego_move.social_move` 一本から family/style へ移行する。

### Step 3

`RepairPolicyNode` を追加する。

### Step 4

`expression_realizer` を repair frame 入力前提に変更する。

### Step 5

`fidelity_gate` に persona flattening 判定を追加する。

### Step 6

eval に persona separation suite を追加する。

## 9. 何をやらないか

次は避けるべきである。

- 語尾辞書だけで persona を分ける
- few-shot を大量に足して表層差分だけを作る
- repair 文面テンプレを persona ごとに手で増やす
- realizer prompt にキャラ説明を直接盛る

これらは短期的には効いても、構造問題を隠すだけである。

## 10. 最終方針

本件の本質は、

- 「どう言うか」の問題ではなく
- 「どう受け取る人格なのか」を state と policy で持てていない

ことにある。

したがって改善の主軸は、

1. persona-specific relational policy を持つ
2. ego move を family/style に分解する
3. residue を持続化する
4. repair を専用 policy node で扱う
5. fidelity gate で flattening を落とす

の 5 点である。

これを実装できれば、

- `warm_guarded_companion` は短く受けるが保護的
- `cold_attached_idol` は受けても刺を残す
- `angelic_but_deliberate` は優位を崩さず受ける
- `irresistibly_sweet_center_heroine` は承認と包摂で受ける

という差を、表層の演技ではなく algorithm として保てる。
