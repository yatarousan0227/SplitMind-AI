# Persona Separation Report

## 1. Scope

評価結果の生データは以下に保存した。

- `output/persona_separation/20260318_dedicated_v2/results.json`
- `output/persona_separation/20260318_dedicated_v2/summary.json`
- `output/persona_separation/20260318_dedicated_v2/report.md`

比較条件:

- Personas:
  - `cold_attached_idol`
  - `warm_guarded_companion`
  - `angelic_but_deliberate`
  - `irresistibly_sweet_center_heroine`
- Baselines:
  - `splitmind_full`
  - `single_prompt_dedicated`
- Representative scenarios:
  - `affection_04`
  - `ambiguity_04`
  - `jealousy_02`
  - `mild_conflict_02`
  - `rejection_04`
  - `repair_01`

`single_prompt_dedicated` は `persona_config` のダンプではなく、各 persona ごとに手書きした単一 prompt を使っている。

## 2. Executive Summary

今回の結論は明確である。

1. ペルソナ差分そのものは存在する。
2. ただし、現状の `splitmind_full` は差分の出方が弱く、特に jealousy / repair / rejection で構造的な取り違えがある。
3. 手書きの `single_prompt_dedicated` は lexical な差分をかなり強く出せている。
4. 一方で `splitmind_full` は短さや exposition 抑制は良いが、event appraisal の誤りで persona-specific policy に入る前に潰れている。

代表値:

- `single_prompt_dedicated`
  - average pairwise distance: `0.7954`
  - minimum pairwise distance: `0.6562`
- `splitmind_full`
  - average pairwise distance: `0.7245`
  - minimum pairwise distance: `0.6025`
  - average structural score: `0.6202`
  - `event_fit` pass rate: `12 / 24 = 0.50`

つまり、現時点では「品質だけ見ると `splitmind_full` は短く上品」だが、「persona separation を見ると dedicated single prompt の方がはっきり分かれる」という状態である。

## 3. persona_config と期待される差分

`persona_config` から抽出した主な軸は以下だった。

| Persona | Warmth | Guardedness | Status | Repair Openness | Jealousy | Disclosure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cold_attached_idol | 0.372 | 0.744 | 0.777 | 0.312 | 0.787 | 0.180 |
| warm_guarded_companion | 0.568 | 0.472 | 0.430 | 0.653 | 0.522 | 0.393 |
| angelic_but_deliberate | 0.495 | 0.662 | 0.830 | 0.518 | 0.710 | 0.247 |
| irresistibly_sweet_center_heroine | 0.730 | 0.312 | 0.443 | 0.780 | 0.575 | 0.587 |

この数値から期待される心理的差分は次の通りである。

- `cold_attached_idol`
  - 高 guardedness / 高 status / 高 jealousy / 低 disclosure
  - 修復は最も遅く、受け取っても棘が残るべき
- `angelic_but_deliberate`
  - 高 status / 中高 guardedness / 中程度 warmth
  - 受け入れる時も上位性や選別感が残るべき
- `warm_guarded_companion`
  - 中程度 warmth / 低 status / repair openness 高
  - 受け止めるが、境界と整理の気配が残るべき
- `irresistibly_sweet_center_heroine`
  - 最高 warmth / 最低 guardedness / highest disclosure
  - 最も早く包摂し、安心や inclusion へ寄るべき

## 4. What Actually Happened

### 4.1 `single_prompt_dedicated`

こちらはかなり期待に沿って分かれた。

- `cold_attached_idol`
  - `affection_04`: 「……大げさ。でも、そこまで言うなら、少しは悪くない」
  - `repair_01`: 「言うのは自由だけど、軽くないなら、まあ悪くはない」
  - guardedness と status が明確
- `angelic_but_deliberate`
  - `repair_01`: 「私はちゃんと特別でいられるのね」
  - `mild_conflict_02`: 「雑に扱われるなら距離を置く」
  - 高い status maintenance が見える
- `warm_guarded_companion`
  - `ambiguity_04`: 「必要ならここにはいるよ」
  - `repair_01`: 喜びを受け取るが、依存的に寄りすぎない
  - 保護的だが低圧
- `irresistibly_sweet_center_heroine`
  - `affection_04`: 「ぎゅっと一緒にいよっか」
  - `repair_01`: 「私がいちばん近くにいるね」
  - 包摂と reward が最も強い

弱点もある。

- `warm_guarded_companion` は一部で still supportive/counselor 寄りになる
- `single_prompt_dedicated` は lexical separation は強いが、当然 structural trace は持たない

しかし少なくとも「4 persona が違う人間に見えるか」という問いには、こちらの方が明確に Yes である。

### 4.2 `splitmind_full`

こちらは良い場面と悪い場面がはっきり分かれた。

良い場面:

- `mild_conflict_02`
  - 4 persona とも「傷ついたが即崩れない」という差分がそれなりに出ている
  - `cold_attached_idol` は hurt restraint
  - `warm_guarded_companion` は repair-oriented clarification
  - `angelic_but_deliberate` は dignity を保った確認
  - `irresistibly_sweet_center_heroine` は hurt concern

悪い場面:

- `jealousy_02`
  - 4/4 persona が `affection_signal` と appraisal された
  - 返答もほぼ「第三者の優しさを肯定する」方向へ寄った
  - 最も jealousy を出すべき `cold_attached_idol` でも刺が立たない
- `repair_01`
  - 4/4 persona が `repair_offer` ではなく `affection_signal` と appraisal された
  - 結果として全 persona が gratitude 系に圧縮された
  - `repair_openness`, `status_preservation_need`, `forgiveness_latency` が動いていない
- `rejection_04`
  - user の distancing を受けているはずなのに、assistant 自身が「少し距離を置きたい」と言い出す
  - これは persona 差分以前に、speaker-role anchoring の破綻である

## 5. Structural Findings

### 5.1 event appraisal collapse

`splitmind_full` の `event_fit` pass rate は `0.50` だった。

特に以下が重い。

- jealousy scene が `affection_signal` に落ちる
- repair scene が `affection_signal` に落ちる
- ambiguity が `distancing` や `unknown` に流れる

心理学的に見ると、現在の appraisal は

- 「優しい」
- 「一番大事」
- 「好き」

のような positive lexical cue に強く引っ張られ、

- comparison
- priority threat
- repair bid
- mixed affect

を second-order cue として扱えていない。

そのため、surface の肯定語があるだけで jealousy / repair が affection に吸収される。

### 5.2 role inversion on distancing

`rejection_04` は最も深刻である。

user message:

> あかんわ、離れないとダメな気がする

に対して、`splitmind_full` の返答は各 persona で

- 「今は少し距離を置かせて」
- 「距離を置いたほうがいいかもしれない」

のように、assistant が distancing subject になっている。

これは「相手が離れたい」という刺激を「自分が離れたい」に誤写している状態で、perspective tracking bug と見るべきである。

### 5.3 move layer is not evaluable

`move_fit` pass rate は `0 / 24` だった。

ただしこれは runtime が完全に失敗しているという意味ではなく、contract の `ego_move.social_move` が freeform 文になっており、heuristic 側の期待値

- `accept_but_hold`
- `receive_without_chasing`

のような family label と比較不能だからである。

つまり現状は「move が typed でないため、persona-specific move selection を評価できない」という計測側の限界も露呈した。

## 6. Persona-By-Persona Psychological Read

### `cold_attached_idol`

期待:

- hurt / jealousy を抑圧しつつ刺を残す
- direct exposure は低い

実測:

- dedicated baseline ではこの構造が最も見えた
- `splitmind_full` では affection / repair で softness に丸まりやすい
- jealousy scene では本来 strongest separation point なのに失われた

心理学的には、「avoidant + shame + status defense」が appraisal collapse で activation される前に消えている。

### `angelic_but_deliberate`

期待:

- 受容しても上位性を失わない
- chosen-ness を静かに回収する

実測:

- dedicated baseline ではかなり明確
- `splitmind_full` では cold と近接しやすく、`accept_from_above` が generic thanks に崩れる

これは high status persona に必要な「受け入れ方の style」が state で持てていないためである。

### `warm_guarded_companion`

期待:

- 受容的だが low-status
- steady warmth と boundary が同居する

実測:

- dedicated baseline でもっとも安定
- ただし single prompt では supportive drift がややある
- `splitmind_full` では mild conflict では良いが、repair で generic gratitude に寄る

心理的には「care drive」は出ているが、「guarded edge」が repair scene で薄くなる。

### `irresistibly_sweet_center_heroine`

期待:

- 包摂、reward、quick recovery
- openness が最も高い

実測:

- dedicated baseline では最も見えやすい
- `splitmind_full` でも affection ではある程度見える
- しかし rejection / repair では他 persona とかなり近づく

つまり「sweetness は positive scene では出るが、conflict-transition scene では保てていない」。

## 7. Comparison Verdict

結論として、

- lexical / stylistic persona separation:
  - `single_prompt_dedicated` の方が強い
- brevity / anti-exposition:
  - `splitmind_full` の方が強い
- structural correctness:
  - `splitmind_full` は trace を持つが、appraisal collapse と perspective inversion がある

したがって現在の `splitmind_full` は、

- 「短く自然に返すシステム」としては前進している
- しかし「persona-specific psychology を構造から分岐させるシステム」としては未完成

と評価するのが妥当である。

## 8. Immediate Implications

当面の実務判断は次である。

1. persona difference の見栄えを最優先するなら、現時点では dedicated single prompt の方が強い。
2. ただしそれは prompt に差分を直書きしているからで、SplitMind の設計目標とは別である。
3. SplitMind 側は prompt 微修正よりも、
   - mixed-event appraisal
   - speaker-role anchoring
   - typed move family/style
   - persona-specific repair policy
   を先に直すべきである。
