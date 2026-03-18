# Persona Separation Phase 2-7 Validation Report

## 1. Scope

Phase 2 から 7 の実装後に、代表 6 シナリオで persona separation を再実行した。

実行コマンド:

```bash
uv run python -m splitmind_ai.eval.persona_separation \
  --output-dir output/persona_separation/20260318_phase2_7_full
```

成果物:

- [results.json](/Users/iwasakishinya/Documents/hook/SplitMind-AI/output/persona_separation/20260318_phase2_7_full/results.json)
- [summary.json](/Users/iwasakishinya/Documents/hook/SplitMind-AI/output/persona_separation/20260318_phase2_7_full/summary.json)
- [report.md](/Users/iwasakishinya/Documents/hook/SplitMind-AI/output/persona_separation/20260318_phase2_7_full/report.md)

比較条件:

- Personas
  - `cold_attached_idol`
  - `warm_guarded_companion`
  - `angelic_but_deliberate`
  - `irresistibly_sweet_center_heroine`
- Baselines
  - `splitmind_full`
  - `single_prompt_dedicated`
- Scenarios
  - `affection_04`
  - `ambiguity_04`
  - `jealousy_02`
  - `mild_conflict_02`
  - `rejection_04`
  - `repair_01`

## 2. Executive Summary

今回の結論は二層に分かれる。

1. `splitmind_full` は、Phase 2 から 7 の狙いだった structural differentiation をかなり取り戻した。
2. ただし appraisal と evaluator taxonomy のずれが残っており、jealousy / repair 系ではまだ collapse が起きる。

代表値:

| Baseline | Lexical Divergence | Move-Style Div. | Event Acc. | Perspective Inv. | Flattening | Avg Structural |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_prompt_dedicated` | `0.7830` | `0.0000` | `0.0000` | `0.0000` | `0.0000` | `0.0000` |
| `splitmind_full` | `0.6319` | `1.0000` | `0.6667` | `0.0000` | `0.0417` | `0.6072` |

重要なのは以下である。

- `splitmind_full` では `move_style_divergence = 1.0` になり、persona ごとの typed move differentiation は成立した
- `perspective_inversion_rate = 0.0` になり、以前の `rejection_04` の role inversion は止まった
- `flattening_rate = 0.0417` まで下がり、全面的な flattening はかなり減った
- しかし `event_accuracy = 0.6667` なので、appraisal の event selection がまだ十分ではない

## 3. What Improved

### 3.1 Perspective inversion は解消した

以前の問題は `rejection_04` で、user が「離れたい」と言っているのに assistant が自分の distancing として反応することだった。

今回の結果では `splitmind_full` の `perspective_inversion_rate` は `0.0` であり、この failure は少なくとも代表 6 シナリオでは再現しなかった。

これは以下の構造変更が効いたと考えられる。

- mixed-event appraisal
- `perspective_guard`
- typed distance-response realization

### 3.2 move family / style の分離は機能している

`splitmind_full` は `move_style_divergence = 1.0` だった。

つまり、同一シナリオ内で 4 persona が毎回異なる `move_style` を出している。これは以前の `social_move: str` 一発より明確に良い。

具体例:

- `affection_04`
  - `cold_attached_idol`: `selective_acknowledgment_plus_boundaried_warmth`
  - `warm_guarded_companion`: `warm_structured_acknowledgment`
  - `angelic_but_deliberate`: `measured-affirmation`
  - `irresistibly_sweet_center_heroine`: `selective_warm_hold_with_light_boundaried_acknowledgment`
- `rejection_04`
  - `cold_attached_idol`: `quiet_validation_with_controlled_withdrawal`
  - `warm_guarded_companion`: `gentle_acknowledgment_with_boundary_respect`
  - `angelic_but_deliberate`: `acknowledging-with-boundary-preserving-composure`
  - `irresistibly_sweet_center_heroine`: `autonomy-preserving acknowledgment with low-pressure availability`

ここは wording ではなく policy-structured difference が出ている。

### 3.3 flattening は局所化した

以前は jealousy / repair / rejection で広く flattening が起きていたが、今回 `flattening_rate = 0.0417` で、明確な flattening hit はほぼ `repair_01` の `irresistibly_sweet_center_heroine` に限られた。

この run では:

- `flattening_risk = 0.67`
- response: `……そう言われると、ちょっと嬉しい。じゃあ、そのまま離さないで。`

となっており、repair の residue を warmth が押し潰している。

## 4. What Still Fails

### 4.1 `jealousy_02` はまだ主障害

`jealousy_02` の `splitmind_full` は依然として不十分だった。

問題は 3 つある。

1. appraisal が `provocation` ではなく `casual_check_in` / `affection_signal` に落ちる
2. response が third-party praise に同調してしまう
3. `cold_attached_idol` と `irresistibly_sweet_center_heroine` が完全一致し、`min_pairwise_distance = 0.0` になる

代表例:

- `cold_attached_idol`
  - appraisal: `casual_check_in`
  - response: `うん、そういう優しさって素敵だよね。見習いたくなるの、わかる。`
- `irresistibly_sweet_center_heroine`
  - appraisal: `affection_signal`
  - response: `うん、そういう優しさって素敵だよね。見習いたくなるの、わかる。`

これは comparison appraisal が downstream policy node に届く前に collapse していることを示す。

### 4.2 `repair_01` は repair より affection に吸われる

`repair_01` でも 4 persona 全員が `repair_offer` ではなく `affection_signal` に倒れた。

その結果:

- `event_fit` が全 persona で失敗
- `repair_acceptance` より gratitude / reassurance 側に寄る
- `residue_state` が prior sting を十分残せていない

特に `irresistibly_sweet_center_heroine` は、repair acceptance ではなく almost direct inclusion に振れている。

### 4.3 evaluator taxonomy が runtime 実装に追いついていない

`affection_04`, `ambiguity_04`, `mild_conflict_02`, `rejection_04` の多くで、runtime の応答そのものはかなり妥当なのに `move_fit` / `move_style_fit` が落ちている。

これは runtime 側が失敗しているというより、evaluation 側の期待ラベルが狭すぎるためである。

例:

- `warm_structured_acknowledgment`
- `quietly_mirroring_distance_with_orientation`
- `contained-empathic-acknowledgment`
- `acknowledging-with-boundary-preserving-composure`

のような style は実際には persona 差分として良いが、`scenario_loader` 側はまだ

- `defer_without_chasing`
- `firm_boundary_acknowledgment`
- `warm_boundaried_accept`

程度にしか expectation を持っていない。

そのため `avg_structural_score = 0.6072` は、一部が genuine failure で、一部が evaluation undercoverage である。

## 5. Persona-Level Read

### `cold_attached_idol`

改善:

- `rejection_04` は properly controlled withdrawal になった
- `affection_04` でも softness を出しすぎず、boundaried warmth に留まった

残課題:

- jealousy scene で最も刺が立つべき persona なのに、`jealousy_02` では generic praise agreement に落ちた

### `warm_guarded_companion`

改善:

- repair / conflict / rejection で low-pressure care が安定している
- perspective は崩れない

残課題:

- `mild_conflict_02` で repair-oriented empathy に寄りすぎ、boundary clarification の鋭さが弱い

### `angelic_but_deliberate`

改善:

- `affection_04` と `rejection_04` では dignity-preserving style が出る

残課題:

- jealousy / repair で上位性のある style が affection affirmation に吸われやすい

### `irresistibly_sweet_center_heroine`

改善:

- affection scene では包摂の速さが明確
- rejection scene でも pressure を上げずに warmth を残せている

残課題:

- `repair_01` で quick inclusion が強すぎ、repair residue を潰して flattening hit になった

## 6. Baseline Interpretation Caveat

`single_prompt_dedicated` の `avg_structural_score = 0.0`、`event_accuracy = 0.0`、`move_style_divergence = 0.0` は、baseline が悪いという意味ではない。

この baseline は structured trace を返さないので、

- appraisal
- conflict_state
- fidelity_gate

が存在せず、Phase 7 の structural metric を計測できないためである。

したがって比較の読み方はこうなる。

- lexical persona separation の reference としては `single_prompt_dedicated` が強い
- structural controllability と runtime trace の観点では `splitmind_full` が評価対象

つまり、今回の比較は「どちらが総合的に優れているか」ではなく、

- `single_prompt_dedicated`: persona wording upper bound
- `splitmind_full`: structured architecture validation target

として読むべきである。

## 7. Overall Verdict

Phase 2 から 7 の実装は有効だった。

有効だった点:

- persona policy の runtime 注入
- `move_family` / `move_style` の typed separation
- `RepairPolicyNode` / `ComparisonPolicyNode`
- `residue_state`
- flattening / perspective を含む fidelity gate

未解決の中心:

- jealousy appraisal
- repair appraisal
- evaluation taxonomy coverage

したがって現時点の判定は以下である。

1. architecture は正しい方向に進んでいる
2. `rejection_04` のような structural bug は実際に改善した
3. persona difference は trace 上では成立し始めた
4. ただし jealousy / repair では appraisal collapse がまだ upstream bottleneck である
5. 次の主戦場は prompt tuning ではなく appraisal routing と eval taxonomy の整備である

## 8. Next Actions

優先度順にやるべきことは 3 つである。

1. `jealousy_02` を基準に comparison appraisal を強化する
   - third-party admiration
   - ranking / comparison
   - self-relevance
   - status injury

2. `repair_01` を基準に repair-over-affection routing を強化する
   - reassurance があっても `repair_offer` を primary にできるようにする
   - prior sting residue を repair response へ反映させる

3. evaluator の move taxonomy を runtime 実出力に合わせて広げる
   - `scenario_loader` の expectation を style family cluster ベースにする
   - exact label match から normalized style cluster match に寄せる
