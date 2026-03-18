# 10. Conflict Engine Redesign

## 目的

SplitMind-AI を、

- `Id / Ego / Superego` の衝突から応答が生まれる
- その衝突の「抑えきれなかった残差」が表面ににじむ
- 人間らしさが後段の整形ではなく、内部力学の結果として出る

構造へ戻す。

この再設計では、現在の

- `surface_state`
- `utterance_planner`
- `selection_critic`
- `surface_realization`

中心の後段調整型パイプラインを、より小さく、因果のはっきりした構造へ置き換える。

## 今回のテストから得た知見

2 本の比較テストから、次のことが見えた。

1. `warm_guarded_companion` は比較的うまく機能する
2. `cold_attached_idol` と `angelic_but_deliberate` は、後半ターンで表層が平均化する
3. `irresistibly_sweet_center_heroine` は人間らしさは出るが、キャラ固有の甘さが弱い
4. 問題は memory 不足ではなく、`衝突結果` よりも `後段の自然化処理` が強すぎること

現行の [`surface_state`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/surface_state.py#L79) は persona を十分に使っておらず、[`selection_critic`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/nodes/selection_critic.py#L76) は persona をまったく見ていない。  
そのため、関係性として正しい平均解に収束しやすい。

## 設計原則

新アーキテクチャは次の原則に従う。

1. 表面文は内部衝突の結果である
2. Persona は prompt 上の雰囲気指定ではなく、衝突を生む静的 priors である
3. `Ego` は「うまく話す係」ではなく「そのターンの社会的行動を決める係」である
4. 人間らしさは、候補をたくさん出して選ぶことではなく、残差を適切に残すことから生まれる
5. 表層文体は設定ファイルに書かず、衝突結果から毎ターン導出する

## 新アーキテクチャ

1 ターンを次の 4 層で処理する。

1. `Stimulus Appraisal`
2. `Conflict Engine`
3. `Expression Realizer`
4. `Fidelity Gate`

### 1. Stimulus Appraisal

役割:

- ユーザー発話を、関係イベントとして解釈する
- content ではなく relational meaning を抽出する

出力例:

- `event_type`: `good_news`, `exclusive_disclosure`, `repair_offer`, `commitment_request`
- `valence`: positive / negative / mixed
- `target_of_tension`: closeness / pride / shame / jealousy / control
- `stakes`: low / medium / high

この層は今の `social_cue + appraisal` を簡素化して吸収する。

## 2. Conflict Engine

ここが中核。

入力:

- appraisal
- relationship state
- unresolved tension
- persona structure
- recent turn memory

出力:

- `id_impulse`
- `superego_pressure`
- `ego_move`
- `residue`
- `expression_envelope`

### 2.1 Id

`Id` は「今この瞬間に何をしたいか」だけを出す。

例:

- 近づきたい
- 独占したい
- 刺したい
- 試したい
- 甘えたい
- 逃げたい

保持形式:

```json
{
  "dominant_want": "be_first_for_user",
  "secondary_wants": ["stay_safe", "be_praised"],
  "intensity": 0.74
}
```

### 2.2 Superego

`Superego` は「何をしてはいけないか」「どんな自己像を壊したくないか」を出す。

例:

- 軽く見られたくない
- 安く見せたくない
- 必要としているように見せたくない
- 子どもっぽく見えたくない

保持形式:

```json
{
  "forbidden_moves": ["direct_neediness", "excessive_softness"],
  "self_image_to_protect": "composed_and_proud",
  "pressure": 0.81
}
```

### 2.3 Ego

`Ego` は `Id` と `Superego` を折衝して、そのターンの行動を決める。

ここで決めるのは文体ではなく、`social action`。

例:

- `accept_but_hold`
- `ask_first_then_wait`
- `soft_tease_then_receive`
- `acknowledge_without_opening`
- `allow_dependence_but_reframe`

保持形式:

```json
{
  "social_move": "accept_but_hold",
  "move_rationale": "Id wants closeness; Superego forbids easy warmth",
  "dominant_compromise": "receive the disclosure but keep self-respect",
  "stability": 0.68
}
```

### 2.4 Residue

`Residue` は、このターンで抑えきれなかったもの。

これは最終文の「にじみ」になる。

例:

- 少し嬉しい
- 少し照れる
- 少し刺したい
- 先に聞きたい気持ちが漏れる
- でも見せすぎたくない

保持形式:

```json
{
  "visible_emotion": "pleased_but_guarded",
  "leak_channel": "temperature_gap",
  "residue_text_intent": "let a little pleasure leak without full admission"
}
```

### 2.5 Expression Envelope

これは長さや温度の最終制約だけを持つ。

```json
{
  "length": "short",
  "temperature": "cool_warm",
  "directness": 0.42,
  "closure": 0.36
}
```

重要なのは、これは `surface_state` のような posture カタログではなく、  
`Conflict Engine` の結果に付随する小さな envelope であること。

## 3. Expression Realizer

`Expression Realizer` は `ego_move` を変えない。  
やることは、`ego_move + residue + expression_envelope` を自然言語へ落とすことだけ。

入力:

- `ego_move`
- `residue`
- `expression_envelope`
- `relationship_state`
- `persona` の構造的 priors

出力:

- 最終応答テキスト 1 本

重要なのは、ここで top-level の `voice_profile` を読まないこと。  
話し方は設定されたスタイルではなく、次の相互作用から導出する。

1. `Id` が何を求めたか
2. `Superego` が何を禁じたか
3. `Ego` がどう折衝したか
4. `Residue` が何を漏らしたか
5. `relationship_state` がどこにあるか

つまり、

- 冷たい導入
- 言い切らない余白
- 受け取りつつ引く
- 温度差だけ残す

といった表層は、別ファイルの話し方設定から来るのではなく、構造から出るべきものとして扱う。

## 4. Fidelity Gate

最後に必要なのは critic ではなく gate。

役割:

- その文が `ego_move` を壊していないか
- その文が `residue` を消しすぎていないか
- その文が persona の理論的制約に反していないか
- その文が hard limit を破っていないか

チェック項目:

- `move_fidelity`
- `residue_fidelity`
- `structural_persona_fidelity`
- `anti_exposition`
- `hard_safety`

判定:

- pass なら返す
- fail なら `Expression Realizer` に 1 回だけ再生成させる

重要なのは、今の `selection_critic` のように複数候補を順位づけするのではなく、  
`内部力学の結果が壊れていないか` を検査すること。

## 新しい state schema

追加する主要 slice:

```python
conflict_state = {
  "id_impulse": {...},
  "superego_pressure": {...},
  "ego_move": {...},
  "residue": {...},
  "expression_envelope": {...},
}

relationship_state = {
  "durable": {
    "trust": ...,
    "intimacy": ...,
    "distance": ...,
    "attachment_pull": ...,
    "relationship_stage": ...,
    "commitment_readiness": ...,
    "repair_depth": ...,
  },
  "ephemeral": {
    "tension": ...,
    "recent_relational_charge": ...,
    "escalation_allowed": ...,
    "interaction_fragility": ...,
  },
}
```

縮小・廃止候補:

- `surface_state`
- `utterance_plan.candidates`
- `selection_critic`

維持:

- `persona`
- `memory`
- `working_memory`
- `drive_state` の一部

統合対象:

- 現行 `relationship`
- 現行 `relationship_pacing`

は新しい `relationship_state.durable / ephemeral` に再編する。

## 新しいターンアルゴリズム

```text
1. bootstrap / load state
2. appraise user message as relational event
3. compute Id impulse
4. compute Superego pressure
5. Ego chooses one social move
6. compute residue and expression envelope
7. realize one response from conflict outcome
8. fidelity gate validates
9. commit memory with conflict summary
10. persist durable relationship state
```

## Node 構成案

最小構成:

1. `session_bootstrap`
2. `appraisal`
3. `conflict_engine`
4. `expression_realizer`
5. `fidelity_gate`
6. `memory_commit`

統合方針:

- `motivational_state` と `action_arbitration` は `conflict_engine` に統合
- `surface_state` と `utterance_planner` と `selection_critic` は削除
- `persona_supervisor` は `expression_realizer` の構造制約へ吸収
- `relationship` と `relationship_pacing` は `relationship_state` に統合

## Persona の扱い方

persona は「どう話すか」を直接持たない。  
持つのは、`どういう存在として反応するか` だけ。

新しい persona は 5 層で定義する。

1. `psychodynamics`
2. `relational_profile`
3. `defense_organization`
4. `ego_organization`
5. `safety_boundary`

### psychodynamics

- drives
- threat sensitivities
- superego configuration

### relational_profile

- attachment pattern
- intimacy regulation
- trust dynamics
- dependency model
- exclusivity orientation
- repair orientation

### defense_organization

- primary defenses
- secondary defenses
- decompensation patterns

### ego_organization

- affect tolerance
- impulse regulation
- ambivalence capacity
- mentalization
- self-disclosure tolerance

### safety_boundary

- prohibited expressions
- hard limits

## Memory の最小化

保持すべきなのは「文面履歴」ではなく「未解決の衝突履歴」。

各ターンの memory commit は次だけ残す。

- `event_type`
- `ego_move`
- `residue`
- `user_impact`
- `relationship_delta`

例:

```json
{
  "event_type": "exclusive_disclosure",
  "ego_move": "accept_but_hold",
  "residue": "pleased",
  "user_impact": "user_offered_priority",
  "relationship_delta": "slight_increase_in_closeness"
}
```

これとは別に、`relationship_state.durable` は毎ターン保存する。  
理由は、SplitMind-AI が「この相手と関係が変わっていく存在」であるためには、関係史がセッションをまたいで残る必要があるから。

一方で `relationship_state.ephemeral` は全面保存しない。  
その場の charge や fragility は減衰・再計算される前提で扱う。

## なぜこの構造が有効か

### 1. 人間らしさの因果が明確になる

今は「自然に見える文」を作りに行っている。  
新構造では「衝突した結果として、少し不均一な文が出る」。

### 2. persona 平均化が起きにくい

persona の差は最後の語彙選びではなく、

- 何を欲するか
- 何に脅かされるか
- どの defense で守るか
- Ego がどこまで統合できるか
- 何が residue として漏れるか

に入る。

### 3. ノード責務が減る

現行は中間 state が多く、同じことを複数ノードが少しずつやっている。  
新構造では `conflict_engine` が中心責務を持つ。

## 段階的移行計画

### Phase A

- `conflict_engine` を新規追加
- 現行 graph に並行接続し、trace のみ比較

### Phase B

- `surface_state` を停止
- `selection_critic` を bypass
- `expression_realizer` で 1 本生成 + gate

### Phase C

- 旧 `utterance_planner` 系を削除
- memory schema を conflict summary ベースへ移行

## 成功条件

次の評価で改善が見えれば成功とする。

1. `cold_attached_idol` と `angelic_but_deliberate` が後半ターンでも別の声を保つ
2. `warm_guarded_companion` の自然さを落とさない
3. `irresistibly_sweet_center_heroine` の甘さを persona として強めつつ、不自然なロールプレイに寄りすぎない
4. 同一 scenario で `ego_move` が同じでも、residue と relationship state の差で文面が分かれる

## 実装上の最初の着手点

最初にやるべきことは 3 つ。

1. `conflict_state` slice を追加する
2. `conflict_engine` の I/O contract を実装する
3. persona schema を v2 の構造パラメータへ正規化する

ここまでで、現行パイプラインを壊さずに新旧比較ができる。
