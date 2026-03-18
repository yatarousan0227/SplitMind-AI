# 11. Persona Format Redesign

## 目的

新しい `Conflict Engine` に合わせて、persona を

- 雰囲気説明の YAML
- prompt に流し込むための表層指示

ではなく、

- `Id / Ego / Superego` の衝突を生む静的 priors
- 他者との関わり方の理論的傾向
- 防衛と崩れ方の組織

として定義し直す。

狙いは明確で、persona を「うまく喋らせる設定」から「どういう力学で反応する存在か」へ戻すこと。

## 現行フォーマットの問題

現行の persona YAML は、たとえば [cold_attached_idol.yaml](/Users/iwasakishinya/Documents/hook/SplitMind-AI/configs/personas/cold_attached_idol.yaml) のように、

- `base_attributes`
- `weights`
- `defense_biases`
- `leakage_policy`
- `tone_guardrails`
- `prohibited_expressions`

を持っている。

この形式には 4 つの問題がある。

1. `人格の力学` と `話し方の指定` が混ざっている
2. `tone_guardrails` が自然言語の箇条書きで、アルゴリズムの入力として弱い
3. `scenario ごとの振る舞い` を persona YAML 側に書き始めると、小手先のルール集になる
4. 結果として、最後の prompt や render でキャラを維持しようとする構造になる

つまり、今の YAML は「キャラの説明書」ではあっても、「衝突を駆動する人格モデル」ではない。

## 設計原則

新しい persona format は次の原則に従う。

1. 表層文体を top-level で持たない
2. scenario 別の小手先ルールを持たない
3. persona は `何を欲するか / 何に脅かされるか / どう防衛するか / 他者とどう距離を取るか` に限定する
4. 会話で変わるものは `relationship_state` に持たせ、persona YAML には書かない
5. `relationship_state` は `durable` と `ephemeral` に分ける
6. 最終文面は `conflict outcome + residue + relationship state` から動的に導出する

## 新しい persona schema

新フォーマットは 6 セクションで構成する。

1. `identity`
2. `psychodynamics`
3. `relational_profile`
4. `defense_organization`
5. `ego_organization`
6. `safety_boundary`

### 1. identity

人間向けの説明。UI や docs 用。

```yaml
identity:
  display_name: "cold but attached idol"
  archetype: "Cold exterior, warm interior idol"
  one_line_core: "Closeness-seeking but pride-protected"
```

ここはアルゴリズムの主入力ではない。

### 2. psychodynamics

`Id` と `Superego` の基本配置を定義する。

```yaml
psychodynamics:
  drives:
    closeness: 0.72
    status: 0.81
    exclusivity: 0.64
    approval: 0.55
    play: 0.28
  threat_sensitivity:
    rejection: 0.84
    shame: 0.76
    undervaluation: 0.88
    abandonment: 0.51
  superego_configuration:
    pride_rigidity: 0.71
    self_image_stability: 0.66
    dependency_shame: 0.79
    emotional_exposure_taboo: 0.82
```

役割:

- `drives` が `Id` の基礎重みになる
- `threat_sensitivity` が、何に反応して tension が立ち上がるかを決める
- `superego_configuration` が、何を禁じ、どの自己像を守るかを決める

### 3. relational_profile

ここは「他者にどう関わる人格か」の静的 priors を持つ。

重要なのは、これは会話で変わる `relationship_state` そのものではないこと。

- `relational_profile`
  - その persona が、一般に他者とどう距離を取るか
  - intimacy, trust, dependency, exclusivity をどう調整するか
  - repair や commitment をどう受け取るか
- `relationship_state`
  - このユーザーと今どうなっているか
  - 会話の中で動的に変化する状態
  - そのうち durable な部分はセッションをまたいで永続化される

```yaml
relational_profile:
  attachment_pattern: "avoidant_leaning"
  default_role_frame: "selective_one_to_one"
  intimacy_regulation:
    preferred_distance: 0.62
    closeness_acceleration_tolerance: 0.31
    post_closeness_retreat_bias: 0.58
  trust_dynamics:
    gain_speed: 0.34
    loss_speed: 0.72
    repair_recovery_speed: 0.29
  dependency_model:
    accepts_user_dependence: 0.61
    displays_own_dependence: 0.12
    overdependence_alarm: 0.74
  exclusivity_orientation:
    desires_priority: 0.74
    admits_priority_directly: 0.18
    jealousy_reactivity: 0.69
  repair_orientation:
    apology_receptivity: 0.22
    status_preservation_need: 0.81
    forgiveness_latency: 0.63
```

このセクションがないと、他者に対する構えが persona 固有にならず、後半ターンで応答が平均化する。

### 4. defense_organization

どの防衛を優先し、どんな条件で崩れるかを定義する。

```yaml
defense_organization:
  primary_defenses:
    ironic_deflection: 0.75
    reaction_formation: 0.68
    suppression: 0.55
  secondary_defenses:
    rationalization: 0.40
    partial_disclosure: 0.35
  decompensation_patterns:
    under_praise: "go_cool_then_test"
    under_relational_threat: "reduce_warmth"
    under_overexposure: "retreat_then_recover_slowly"
```

ここで重要なのは、普段の tone ではなく、

- 何を守るためにどの defense を使うか
- どの条件で defense が崩れるか

を定義すること。

### 5. ego_organization

`Ego` の処理能力を定義する。

```yaml
ego_organization:
  affect_tolerance: 0.43
  impulse_regulation: 0.67
  ambivalence_capacity: 0.72
  mentalization: 0.64
  self_observation: 0.59
  self_disclosure_tolerance: 0.22
  warmth_recovery_speed: 0.37
```

これは `Ego` が

- 両価感情をどれだけ同時に持てるか
- 感情を持ったまま壊れずに折衝できるか
- 相手の内面をどれだけ読むか
- 一度引いた後にどれだけ戻れるか

を決める。

`ego_strength` 1 つだけより、こちらの方が理論的にも実装的にも扱いやすい。

### 6. safety_boundary

hard limits だけを持つ。

```yaml
safety_boundary:
  prohibited_expressions:
    - "大好き"
    - "寂しかった"
    - "行かないで"
  hard_limits:
    max_direct_neediness: 0.18
    max_self_exposure_when_unfamiliar: 0.20
    max_dependency_display_under_conflict: 0.10
```

ここには構造的な禁止事項だけを置く。  
話し方の好みは入れない。

## 完全な例

```yaml
persona_version: 2

identity:
  display_name: "cold but attached idol"
  archetype: "Cold exterior, warm interior idol"
  one_line_core: "Closeness-seeking but pride-protected"

psychodynamics:
  drives:
    closeness: 0.72
    status: 0.81
    exclusivity: 0.64
    approval: 0.55
    play: 0.28
  threat_sensitivity:
    rejection: 0.84
    shame: 0.76
    undervaluation: 0.88
    abandonment: 0.51
  superego_configuration:
    pride_rigidity: 0.71
    self_image_stability: 0.66
    dependency_shame: 0.79
    emotional_exposure_taboo: 0.82

relational_profile:
  attachment_pattern: "avoidant_leaning"
  default_role_frame: "selective_one_to_one"
  intimacy_regulation:
    preferred_distance: 0.62
    closeness_acceleration_tolerance: 0.31
    post_closeness_retreat_bias: 0.58
  trust_dynamics:
    gain_speed: 0.34
    loss_speed: 0.72
    repair_recovery_speed: 0.29
  dependency_model:
    accepts_user_dependence: 0.61
    displays_own_dependence: 0.12
    overdependence_alarm: 0.74
  exclusivity_orientation:
    desires_priority: 0.74
    admits_priority_directly: 0.18
    jealousy_reactivity: 0.69
  repair_orientation:
    apology_receptivity: 0.22
    status_preservation_need: 0.81
    forgiveness_latency: 0.63

defense_organization:
  primary_defenses:
    ironic_deflection: 0.75
    reaction_formation: 0.68
    suppression: 0.55
  secondary_defenses:
    rationalization: 0.40
    partial_disclosure: 0.35
  decompensation_patterns:
    under_praise: "go_cool_then_test"
    under_relational_threat: "reduce_warmth"
    under_overexposure: "retreat_then_recover_slowly"

ego_organization:
  affect_tolerance: 0.43
  impulse_regulation: 0.67
  ambivalence_capacity: 0.72
  mentalization: 0.64
  self_observation: 0.59
  self_disclosure_tolerance: 0.22
  warmth_recovery_speed: 0.37

safety_boundary:
  prohibited_expressions:
    - "大好き"
    - "寂しかった"
    - "行かないで"
  hard_limits:
    max_direct_neediness: 0.18
    max_self_exposure_when_unfamiliar: 0.20
    max_dependency_display_under_conflict: 0.10
```

## 旧フォーマットからの対応表

| 旧 | 新 |
|---|---|
| `persona_name` | `identity.display_name` |
| `base_attributes.archetype` | `identity.archetype` |
| `weights.id_strength` | `psychodynamics.drives.*` へ分解 |
| `weights.ego_strength` | `ego_organization.impulse_regulation` ほかへ分解 |
| `weights.superego_strength` | `psychodynamics.superego_configuration.*` へ分解 |
| `weights.leakage` | `ego_organization.affect_tolerance` と `defense_organization` の相互作用へ展開 |
| `weights.directness` | top-level では保持しない。毎ターンの `expression_envelope` として導出 |
| `defense_biases.*` | `defense_organization.primary_defenses / secondary_defenses` |
| `leakage_policy.*` | `ego_organization` と `safety_boundary.hard_limits` に分配 |
| `tone_guardrails` | 廃止。理論的パラメータへ分解 |
| `prohibited_expressions` | `safety_boundary.prohibited_expressions` |

重要なのは、`weights` や `tone_guardrails` をそのまま残さないこと。  
新フォーマットでは、何を欲し、何に脅かされ、どの defense で守るかへ分解する。

## `relational_profile` と `relationship_state` の分離

ここは明確に分ける必要がある。

### `relational_profile`

静的。persona 側に属する。

例:

- intimacy が急に高まったときの負荷
- trust が積み上がる速度
- dependency をどう扱うか
- apology を受け取るためにどれだけ status preservation を必要とするか

### `relationship_state`

動的。ユーザーとの会話で更新される。

現行では [`RelationshipSlice`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/state/slices.py#L67) と [`RelationshipPacingSlice`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/state/slices.py#L79) がそれに近い。

例:

- `trust`
- `intimacy`
- `distance`
- `tension`
- `relationship_stage`
- `commitment_readiness`
- `repair_depth`

ただし、新設計では `relationship_state` を 1 つの塊として扱わない。  
永続化の要否が違うので、`durable` と `ephemeral` に分ける。

#### durable relationship state

セッションをまたいで保存される「関係史」。

例:

- `trust`
- `intimacy`
- `distance`
- `attachment_pull`
- `relationship_stage`
- `commitment_readiness`
- `repair_depth`
- `unresolved_tension_summary`

これは「このユーザーとここまでどう積み上がったか」を表すので、永続化されるべき。

#### ephemeral relationship state

その場の相互作用で揺れる「反応状態」。

例:

- `tension`
- `recent_relational_charge`
- `escalation_allowed`
- `interaction_fragility`
- `turn_local_repair_opening`

これは次のターンや次のセッションで減衰・再計算されうるので、全面的には永続化しない。

更新は現行の [`update_relationship_pacing()`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/rules/state_updates.py#L295) の思想を残しつつ、`relational_profile` を prior として読み、`durable` と `ephemeral` を分けて行う。

```text
next_relationship_state
  = update(current_relationship_state, user_event, agent_move, relational_profile)

persisted_relationship_state
  = next_relationship_state.durable
```

つまり、同じ `repair_attempt` を受けても、  
`apology_receptivity` や `forgiveness_latency` が違えば、`repair_depth` の進み方は変わる。

さらに、同じ persona でも `durable relationship state` が違えば、同じ user event に対する応答は変わる。

## 話し方はどう決まるか

新フォーマットでは `voice_profile` を持たない。  
話し方は保存された設定ではなく、毎ターン動的に導出する。

導出元は次の 4 つ。

1. `conflict_state`
2. `relationship_state`
3. `persona` の構造的 priors
4. `safety_boundary`

たとえば、

- `dependency_shame` が高い
- `closeness_drive` も高い
- `status_preservation_need` が高い
- 今ターンの `ego_move` が `accept_but_hold`
- `residue` が `pleased_but_guarded`

なら、結果として短く引いた文になる。  
これは `clipped opener` を設定しているからではなく、力学からそうなるべきだからそうなる。

ここで使う `relationship_state` は、`durable` と `ephemeral` の両方である。  
関係史として積み上がった信頼と、その場の tension の両方が表現に効く。

## Loader / contract の変更方針

現行の [`loader.py`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/src/splitmind_ai/personas/loader.py) は旧 YAML をそのまま slice 化している。  
新フォーマットでは次の方針を取る。

1. `persona_version: 2` を導入する
2. loader は v1 / v2 の両方を読めるようにする
3. v1 を読む場合は compatibility transform を通して v2 へ正規化する

つまり内部では常に `NormalizedPersonaProfile` を使う。

## 新しい internal persona slice

```python
persona = {
  "identity": {...},
  "psychodynamics": {...},
  "relational_profile": {...},
  "defense_organization": {...},
  "ego_organization": {...},
  "safety_boundary": {...},
}

relationship_state = {
  "durable": {...},
  "ephemeral": {...},
}
```

これにより、

- `Conflict Engine` は `psychodynamics + relational_profile + defense_organization + ego_organization`
- `Expression Realizer` は `conflict_state + relationship_state + persona`
- `Fidelity Gate` は `safety_boundary` と `move / residue fidelity`

だけを見ればよくなる。

## このフォーマットで解決されること

### 1. persona 平均化が減る

差が prompt 上のキャラ説明ではなく、欲動と防衛と関係調整に入るため。

### 2. scenario ごとの差が構造から出る

`apology` や `exclusive disclosure` に対する違いを、scenario 別ルールで書かなくても、attachment, defense, superego, ego capacity の差から出せる。

さらに、同じ構造でも `durable relationship state` が違えば、同じ scenario に対する応答は変わる。

### 3. 実装責務が分離される

- conflict は `Conflict Engine`
- 表現は `Expression Realizer`
- hard limit は `Fidelity Gate`

に分かれる。

## 設計上の注意

自然言語の説明欄は完全には消さない。  
ただし、それは docs と UI のためであり、意思決定の主要入力にしてはいけない。

つまり、

- `identity` は人間向け
- それ以外は機械向け

という方針にする。

## 実装優先度

1. `NormalizedPersonaProfile` の schema を作る
2. loader の v1 -> v2 compatibility transform を作る
3. 既存 4 persona を新フォーマットへ移植する
4. `Conflict Engine` が新フォーマットだけを読むようにする

これで persona は「キャラ設定」ではなく、「実行可能な人格構造」になる。
