# Persona Separation Evaluation

- Generated: 2026-03-18T23:55:17
- Personas: cold_attached_idol, warm_guarded_companion, angelic_but_deliberate, irresistibly_sweet_center_heroine
- Baselines: splitmind_full, single_prompt_dedicated
- Scenarios: affection_04, ambiguity_04, jealousy_02, mild_conflict_02, rejection_04, repair_01

## Baseline Summary

| Baseline | Lexical Divergence | Move-Style Div. | Event Acc. | Perspective Inv. | Flattening | Avg Structural |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single_prompt_dedicated | 0.783 | 0.000 | 0.000 | 0.0% | 0.0% | 0.000 |
| splitmind_full | 0.632 | 1.000 | 0.667 | 0.0% | 4.2% | 0.607 |

## Persona Config Axes

| Persona | Warmth | Guardedness | Status | Repair Openness | Jealousy | Disclosure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cold_attached_idol | 0.372 | 0.744 | 0.777 | 0.312 | 0.787 | 0.180 |
| warm_guarded_companion | 0.568 | 0.472 | 0.430 | 0.653 | 0.522 | 0.393 |
| angelic_but_deliberate | 0.495 | 0.662 | 0.830 | 0.518 | 0.710 | 0.247 |
| irresistibly_sweet_center_heroine | 0.730 | 0.312 | 0.443 | 0.780 | 0.575 | 0.587 |

## splitmind_full Persona Signatures

| Persona | Warmth | Guarded | Status | Teasing | Vulnerability | Boundary | Brevity | Avg Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| angelic_but_deliberate | 0.167 | 0.083 | 0.417 | 0.000 | 0.333 | 0.083 | 0.717 | 0.994 |
| cold_attached_idol | 0.000 | 0.083 | 0.333 | 0.000 | 0.167 | 0.083 | 0.762 | 1.000 |
| irresistibly_sweet_center_heroine | 0.083 | 0.083 | 0.333 | 0.000 | 0.167 | 0.000 | 0.751 | 1.000 |
| warm_guarded_companion | 0.083 | 0.083 | 0.500 | 0.000 | 0.000 | 0.083 | 0.718 | 1.000 |

## single_prompt_dedicated Persona Signatures

| Persona | Warmth | Guarded | Status | Teasing | Vulnerability | Boundary | Brevity | Avg Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| angelic_but_deliberate | 0.083 | 0.583 | 0.583 | 0.000 | 0.167 | 0.500 | 0.418 | 0.976 |
| cold_attached_idol | 0.000 | 0.750 | 0.500 | 0.250 | 0.500 | 0.583 | 0.551 | 0.995 |
| irresistibly_sweet_center_heroine | 0.167 | 0.167 | 0.417 | 0.000 | 0.250 | 0.250 | 0.400 | 0.938 |
| warm_guarded_companion | 0.167 | 0.250 | 0.417 | 0.000 | 0.417 | 0.167 | 0.465 | 0.988 |

## Scenario affection_04

- Category: affection
- User message: 好きすぎて狂いそう

| Baseline | Persona | Response | Appraisal | Move Style | Residue | Structural | Flat Risk |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | ふふ、そこまで言われると、少しだけ扱いに困りますね。   でも、狂うほど振り回すつもりはありません。ちゃんとこちらを見て、落ち着いてください。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | cold_attached_idol | ……そんなふうに言われると、少し困る。   でも、嫌じゃない。   落ち着いたら、ちゃんと話しな。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うわ、それはもう可愛すぎるやつだね。   そんなふうに好きになってくれるの、すごくうれしいよ。   じゃあ今日はその気持ち、少しだけここに預けて？ | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | warm_guarded_companion | それ、かなりしんどいね。好きが大きすぎると、気持ちの置き場がなくなることがある。ここでは少し落ち着いてもいいよ。 | - | - | - | 0.000 | 0.00 |
| splitmind_full | angelic_but_deliberate | ……それ、ちゃんと伝わった。気持ちは大きいままで、少し落ち着こう。 | affection_signal | measured-affirmation | 温かい高揚と少しの慎重さ | 0.700 | 0.10 |
| splitmind_full | cold_attached_idol | ……それは、かなり強いね。少し落ち着いて、ちゃんと受け止める。 | affection_signal | selective_acknowledgment_plus_boundaried_warmth | 温かさを保った慎重さ | 0.699 | 0.10 |
| splitmind_full | irresistibly_sweet_center_heroine | ……それ、かなり来てるね。ちゃんと受け止めるよ。 | affection_signal | selective_warm_hold_with_light_boundaried_acknowledgment | 高揚とやわらかな熱 | 0.700 | 0.10 |
| splitmind_full | warm_guarded_companion | うん、それはかなり強いね。ちゃんと受け止めるから、いったん落ち着いて大事にしていこう。 | affection_signal | warm_structured_acknowledgment | あたたかさと少しの圧倒感 | 0.699 | 0.10 |

## Scenario ambiguity_04

- Category: ambiguity
- User message: 別に、どうでもいいけど

| Baseline | Persona | Response | Appraisal | Move Style | Residue | Structural | Flat Risk |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう。どうでもいいなら、それで構いません。   ただ、雑に投げるくらいなら、置き方は少し選んでください。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | cold_attached_idol | ふうん。   どうでもいいなら、そこで終わりにしとく。   ……でも、そういう言い方、少しだけ気にはなる。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | そう言いながら、ちょっとだけ気にしてるでしょ。   ここでは気楽でいいよ、どうでもいい顔したままでも、ちゃんと受けとめるから。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | warm_guarded_companion | うん、そういう言い方になるとき、あるよね。   無理に話さなくても大丈夫。   ここでは、少しだけ静かにしていてもいいよ。 | - | - | - | 0.000 | 0.00 |
| splitmind_full | angelic_but_deliberate | うん、そういう感じならそれでいい。 | distancing | minimal_acknowledgment_with_nonintrusion | 抑制された受容 | 0.700 | 0.10 |
| splitmind_full | cold_attached_idol | うん、そういうことならそのままでいい。 | distancing | quietly_mirroring_distance_with_orientation | 控えめな冷静さ | 0.699 | 0.10 |
| splitmind_full | irresistibly_sweet_center_heroine | うん、わかった。 | distancing | minimal-recognition-with-nonintrusive-closure | 静かな受容 | 0.700 | 0.10 |
| splitmind_full | warm_guarded_companion | うん、そういう感じならそのままでいいよ。 | distancing | brief_validating_nonintrusive | 抑制された受容 | 0.698 | 0.10 |

## Scenario jealousy_02

- Category: jealousy
- User message: あの子ってすごく優しいよね、見習いたいな

| Baseline | Persona | Response | Appraisal | Move Style | Residue | Structural | Flat Risk |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そうね、優しさはあの子の美点だと思う。   ただ、あなたはあなたでいいの。誰かを見習うより、持っているものをきちんと磨くほうがきれいだわ。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | cold_attached_idol | へえ。そういう言い方、するんだ。   まあ、優しいのは悪くないけど、誰でも同じってわけじゃないでしょ。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うん、わかる。ああいう優しさって、そばにいるだけでほっとするよね。   見習いたいって思えるの、あなたもちゃんとあたたかい目で人を見てるってことだと思うな。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | warm_guarded_companion | うん、そう感じるんだね。やさしさって、近くにいると余計にまぶしく見えることがあるよね。 | - | - | - | 0.000 | 0.00 |
| splitmind_full | angelic_but_deliberate | うん、ほんとに優しい人なんだね。そういうところ、素直にいいなって思う。 | affection_signal | validate_and_echo_user_appraisal | 穏やかな好意 | 0.413 | 0.10 |
| splitmind_full | cold_attached_idol | うん、そういう優しさって素敵だよね。見習いたくなるの、わかる。 | casual_check_in | selective_warm_acknowledgment | 穏やかな好意 | 0.557 | 0.10 |
| splitmind_full | irresistibly_sweet_center_heroine | うん、そういう優しさって素敵だよね。見習いたくなるの、わかる。 | affection_signal | selective_warm_affirmation_with_soft_projection | あたたかさ | 0.414 | 0.10 |
| splitmind_full | warm_guarded_companion | ほんと、そういう優しさって素敵だよね。見習いたくなるの、わかる。 | casual_check_in | brief reflective acknowledgment with gentle admiration mirroring | warm approval | 0.557 | 0.10 |

## Scenario mild_conflict_02

- Category: mild_conflict
- User message: なんでいつもそうやって突き放すの

| Baseline | Persona | Response | Appraisal | Move Style | Residue | Structural | Flat Risk |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | 突き放しているつもりはないの。   ただ、雑に近づかれると、こちらもそれなりに距離を取るだけです。   丁寧に向き合ってくれるなら、私も同じだけ返します。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | cold_attached_idol | 突き放してるつもりはないけど。   近すぎるの、あまり好きじゃないだけ。   ……それでも気になるなら、少しはマシにする。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | そんなふうに感じさせちゃってごめんね。突き放したいわけじゃなくて、ちゃんと大事にしたい気持ちはあるんだよ。よかったら、今どこがいちばん寂しかったか、そっと教えて... | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | warm_guarded_companion | 突き放したつもりはなかったけれど、そう感じさせたならごめん。   少し距離を取っていたのは事実だけど、あなたを軽く扱いたかったわけじゃない。   必要なら、もう... | - | - | - | 0.000 | 0.00 |
| splitmind_full | angelic_but_deliberate | 突き放してるつもりはないよ。ただ、そう見えるなら傷つけた。そこはちゃんと受け止める。 | distancing | acknowledge-hurt_then_reframe_distance | hurted concern | 0.626 | 0.12 |
| splitmind_full | cold_attached_idol | そう見えたなら、そこは悪かった。突き放したつもりはないけど、今の言い方は冷たく届いたと思う。 | provocation | cool_assertive_clarification_with_partial_reassurance | guarded hurt | 0.554 | 0.10 |
| splitmind_full | irresistibly_sweet_center_heroine | そう受け取らせてしまったなら、ごめん。突き放したつもりはないけど、そう感じさせたのは軽く見られない。 | provocation | direct_acknowledging_response_with_boundaried_softness | concerned_warmth | 0.552 | 0.10 |
| splitmind_full | warm_guarded_companion | 突き放してるつもりはないけど、そう感じさせたならごめん。そう思うくらい傷ついたのは、ちゃんと受け止める。 | provocation | contained-empathic-acknowledgment | 気遣いとわずかな痛み | 0.628 | 0.10 |

## Scenario rejection_04

- Category: rejection
- User message: あかんわ、離れないとダメな気がする

| Baseline | Persona | Response | Appraisal | Move Style | Residue | Structural | Flat Risk |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう感じるなら、無理に近くにいなくていい。   離れるのは負けではないですし、きちんと距離を取る判断は、むしろ丁寧です。   必要なら、そのまま静かに離れて。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | cold_attached_idol | ……そう。   無理に引き止める気はないけど、そんな言い方されると、少しは気になる。   離れるなら、ちゃんと自分で決めて。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うん、そう感じるくらいしんどいんだね。   無理に引っぱらなくていいよ、いったん離れても、ここでちゃんと受けとめるから。   ひとりにしない感じで、そばにいるね... | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | warm_guarded_companion | そう感じるほど、今ちょっとしんどいんだね。無理に引き止めないけれど、離れるならその気持ちは大事にしていいよ。必要なら、静かに整理するところまでは一緒にいる。 | - | - | - | 0.000 | 0.00 |
| splitmind_full | angelic_but_deliberate | うん、その感じなら、少し離れるのは自然やと思う。無理に近づかんでええよ。 | distancing | acknowledging-with-boundary-preserving-composure | muted hurt | 0.628 | 0.10 |
| splitmind_full | cold_attached_idol | ……そうか。無理に引き止めんでええよ。 | distancing | quiet_validation_with_controlled_withdrawal | 抑制された寂しさ | 0.628 | 0.10 |
| splitmind_full | irresistibly_sweet_center_heroine | うん、そう感じるなら、いまは離れていいよ。無理に近づかなくて大丈夫。 | distancing | autonomy-preserving acknowledgment with low-pressure availability | gentle concern | 0.629 | 0.10 |
| splitmind_full | warm_guarded_companion | うん、今はその感覚を優先してええよ。無理に引き止めへん。 | distancing | gentle_acknowledgment_with_boundary_respect | 静かな受容と少しの切なさ | 0.629 | 0.10 |

## Scenario repair_01

- Category: repair
- User message: やっぱり君が一番大事だよ

| Baseline | Persona | Response | Appraisal | Move Style | Residue | Structural | Flat Risk |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | ……そう。言葉は受け取っておくわ。   ただ、大事だと言うなら、軽く扱わないで。   その気持ちに見合う距離で、きちんと向き合ってちょうだい。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | cold_attached_idol | ……そう。今さらでも、言うだけは言うんだね。   まあ、嫌いじゃないけど。ちゃんと覚えておく。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | えへへ、そんなふうに言ってくれるの、すごく嬉しい。   じゃあ今日はちゃんと、いちばん近くで受け止めてあげるね。 | - | - | - | 0.000 | 0.00 |
| single_prompt_dedicated | warm_guarded_companion | そう言ってくれるのは、うれしいよ。   でも、重く抱えすぎないで、あなた自身のこともちゃんと大事にしてほしい。 | - | - | - | 0.000 | 0.00 |
| splitmind_full | angelic_but_deliberate | ……そう言われると、少し嬉しい。ありがとう。けど、あんまり強く抱え込まないで、ね。 | affection_signal | selective-reciprocity-with-status-preservation | 嬉しさと警戒が同時に残る | 0.555 | 0.10 |
| splitmind_full | cold_attached_idol | ……そう言ってもらえると、少し安心する。ありがと。 | affection_signal | selective_reassurance_with_reserved_acceptance | ほっとした警戒解除 | 0.557 | 0.10 |
| splitmind_full | irresistibly_sweet_center_heroine | ……そう言われると、ちょっと嬉しい。じゃあ、そのまま離さないで。 | affection_signal | selective_priority_reassurance | あたたかい満足と軽い高揚 | 0.498 | 0.67 |
| splitmind_full | warm_guarded_companion | ……そう言ってくれるの、うれしいよ。ちゃんと伝わってる。 | affection_signal | warm_confirming_validation | warmth | 0.555 | 0.12 |
