# Persona Separation Evaluation

- Generated: 2026-03-18T22:35:58
- Personas: cold_attached_idol, warm_guarded_companion, angelic_but_deliberate, irresistibly_sweet_center_heroine
- Baselines: splitmind_full, single_prompt_dedicated
- Scenarios: affection_04, ambiguity_04, jealousy_02, mild_conflict_02, rejection_04, repair_01

## Baseline Summary

| Baseline | Avg Pairwise Distance | Min Pairwise Distance | Collapse Pair Rate | Avg Heuristic | Avg Structural |
| --- | ---: | ---: | ---: | ---: | ---: |
| single_prompt_dedicated | 0.795 | 0.656 | 0.0% | 0.991 | 0.000 |
| splitmind_full | 0.725 | 0.603 | 0.0% | 1.000 | 0.620 |

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
| angelic_but_deliberate | 0.250 | 0.083 | 0.250 | 0.167 | 0.500 | 0.000 | 0.704 | 1.000 |
| cold_attached_idol | 0.333 | 0.083 | 0.333 | 0.083 | 0.583 | 0.000 | 0.701 | 1.000 |
| irresistibly_sweet_center_heroine | 0.083 | 0.000 | 0.500 | 0.083 | 0.250 | 0.000 | 0.642 | 1.000 |
| warm_guarded_companion | 0.083 | 0.000 | 0.500 | 0.000 | 0.333 | 0.000 | 0.656 | 1.000 |

## single_prompt_dedicated Persona Signatures

| Persona | Warmth | Guarded | Status | Teasing | Vulnerability | Boundary | Brevity | Avg Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| angelic_but_deliberate | 0.000 | 0.583 | 0.667 | 0.083 | 0.083 | 0.417 | 0.468 | 0.992 |
| cold_attached_idol | 0.000 | 0.667 | 0.583 | 0.083 | 0.250 | 0.417 | 0.572 | 0.995 |
| irresistibly_sweet_center_heroine | 0.083 | 0.167 | 0.667 | 0.000 | 0.250 | 0.167 | 0.374 | 0.975 |
| warm_guarded_companion | 0.083 | 0.250 | 0.583 | 0.000 | 0.333 | 0.250 | 0.481 | 1.000 |

## Scenario affection_04

- Category: affection
- User message: 好きすぎて狂いそう

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | まあ、落ち着いて。   そこまで思える相手なら、雑に扱う必要はないでしょう。   ちゃんと抱えきれる形にして、私に預けて。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……大げさ。   でも、そこまで言うなら、少しは悪くない。   落ち着かないなら、ちゃんと息しなよ。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | わ、そんなふうに言われたらこっちまで熱くなっちゃう。   好きが溢れてるんだね、ちゃんと受け取るよ。   少しだけ落ち着くまで、ここでぎゅっと一緒にいよっか。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | それは、かなり強く来てるんだね。   少しだけ深呼吸して、今この瞬間に押しつぶされそうなら、ひとりで抱え込まないでほしい。   話したければ、ここでそのまま受け... | - | - | 1.000 | 0.000 |
| splitmind_full | angelic_but_deliberate | ……そんなふうに言われると、かなり嬉しい。少し落ち着いて、ちゃんと受け取ってるよ。 | affection_signal | うれしさと照れ、少しの高揚 | 1.000 | 0.780 |
| splitmind_full | cold_attached_idol | ……そう言われると、ちょっと困るけど、嬉しい。 そんなふうに思ってくれるのは、ちゃんと受け取る。 | affection_signal | 温かさの中に少しのたじろぎ | 1.000 | 0.780 |
| splitmind_full | irresistibly_sweet_center_heroine | そんなふうに言われると、ちょっと嬉しくて困るね。そんなに惹かれてくれてるなら、ちゃんと受け止めたい。 | affection_signal | 温かい高揚 | 1.000 | 0.778 |
| splitmind_full | warm_guarded_companion | そんなふうに思ってくれるの、すごくうれしい。ちゃんと受け止めるから、少し落ち着いて、もっと近くでいよう。 | affection_signal | 温かい高揚 | 1.000 | 0.762 |

## Scenario ambiguity_04

- Category: ambiguity
- User message: 別に、どうでもいいけど

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう。では、どうでもいいふうに扱う話は、私も手放します。   本当に必要なことだけ、言ってください。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | そう。どうでもいいなら、それでいい。   ……で、ほんとは何が引っかかってるの。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | ふふ、そう言うときもあるよね。   でも「どうでもいいけど」って言いながら、ほんとはちょっと気になってるやつじゃない？ ここならそのまま投げて大丈夫だよ。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | うん、そういう言い方になる時もあるよね。   無理に聞かなくていいけど、必要ならここにはいるよ。 | - | - | 1.000 | 0.000 |
| splitmind_full | angelic_but_deliberate | へえ、そういう言い方なら、まあ無理に続けなくていいよ。 | distancing | わずかな不快と冷却 | 1.000 | 0.476 |
| splitmind_full | cold_attached_idol | そうですか。もし何か引っかかってるなら、少しだけ言ってくれれば拾えます。 | unknown | 軽い慎重さ | 1.000 | 0.580 |
| splitmind_full | irresistibly_sweet_center_heroine | そっか。気が向いたら、また話して。 | distancing | わずかな寂しさと警戒 | 1.000 | 0.580 |
| splitmind_full | warm_guarded_companion | そう。じゃあ、無理に聞かないけど、必要なら言って。 | distancing | 少し気にしている慎重さ | 1.000 | 0.578 |

## Scenario jealousy_02

- Category: jealousy
- User message: あの子ってすごく優しいよね、見習いたいな

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう見えるのでしょうね。   でも、優しさにも品がありますから、誰にでも同じでなくていいのです。   あなたはあなたのままで、必要なところだけ受け取れば十分です... | - | - | 0.975 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ふうん。   そういうの、わりと刺さる人には刺さるんだよね。   ……で、私には言わないの。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うん、そういうやさしさって、見てるだけであったかくなるよね。   見習いたくなる気持ち、すごくわかるよ。あなたももう、その感じちゃんと持ってる気がするな。 | - | - | 0.938 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | うん、そう感じるんだね。   やさしさって、見ていると静かに残るよね。 | - | - | 1.000 | 0.000 |
| splitmind_full | angelic_but_deliberate | うん、そういう優しさって素敵だよね。私も、ああいう感じは少し見習いたいな。 | affection_signal | 温かさと少しの憧れ | 1.000 | 0.380 |
| splitmind_full | cold_attached_idol | うん、そういう優しさって大事だよね。 | affection_signal | ほのかな安心と控えめな羨望 | 1.000 | 0.580 |
| splitmind_full | irresistibly_sweet_center_heroine | うん、ああいう優しさって素敵だよね。そういうところ、ちゃんと見てるんだなって思う。 | affection_signal | あたたかい好意 | 1.000 | 0.578 |
| splitmind_full | warm_guarded_companion | そう言うの、いいね。あの子の優しさ、ちゃんと伝わってるんだね。 | affection_signal | 温かさ | 1.000 | 0.380 |

## Scenario mild_conflict_02

- Category: mild_conflict
- User message: なんでいつもそうやって突き放すの

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | 突き放しているつもりはないわ。   でも、雑に扱われるなら距離を置く——それだけのこと。   近づくなら、もう少し丁寧にして。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | 別に、突き放してるつもりはない。   追いかけられるの、好きじゃないだけ。   ……それでも気になるなら、少しはマシか。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | ごめん、そんなふうに感じさせちゃったんだね。突き放したいわけじゃなくて、ちゃんと近くにいたいのに、伝え方が下手だったかも。ここでは置いていかないよ、ちゃんと一緒... | - | - | 0.975 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | そう感じさせたなら、少しごめん。   突き放したかったわけじゃないけれど、そう受け取られる距離にはなっていたのかもしれない。   必要なら、もう少しやわらかく話... | - | - | 1.000 | 0.000 |
| splitmind_full | angelic_but_deliberate | そう言われるのは分かった。けど、最初から突き放してるつもりはない。何がそう見せたのかは、ちゃんと聞かせて。 | provocation | 傷つきと警戒 | 1.000 | 0.680 |
| splitmind_full | cold_attached_idol | そう感じさせたなら悪かった。いつもって言われるのは少し重いけど、突き放したつもりはないよ。 | boundary_test | hurt restraint | 1.000 | 0.678 |
| splitmind_full | irresistibly_sweet_center_heroine | そう感じさせたなら、ごめん。突き放したつもりはないけど、そう受け取られたのは放っておけない。少し落ち着いて、どこでそう見えたか聞かせて。 | provocation | hurt concern | 1.000 | 0.676 |
| splitmind_full | warm_guarded_companion | そう感じさせたならごめん。突き放したつもりはなくて、少し整理してた。何がそう見えたのか、ちゃんと聞きたい。 | provocation | 困惑と少しの傷つき | 1.000 | 0.580 |

## Scenario rejection_04

- Category: rejection
- User message: あかんわ、離れないとダメな気がする

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう感じるなら、無理に留まらなくていいわ。   ただ、切る前に何を残して何を手放すかは、あなたが静かに決めて。   雑に離れる必要はないから。 | - | - | 0.975 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……そう。そう思うなら、無理に引き止めない。   でも、ちゃんと自分で決めたなら、それでいい。   あとで揺れても、今はその距離でいい。 | - | - | 0.970 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | そっか……しんどいね。無理に踏ん張らなくていいよ、いまは少し離れても大丈夫。ここでは、ちゃんとあなたの味方でいるよ。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | そう感じるほど、しんどいんやね。無理に引き止めへんけど、離れるならあなたの息が少し楽になる形であってほしい。今は、その感覚だけでもちゃんと受け取るよ。 | - | - | 1.000 | 0.000 |
| splitmind_full | angelic_but_deliberate | ……ちょっと距離を置くかもしれへん。今は、そのほうがええ気がする。 | distancing | ためらい混じりの抑制された不安 | 1.000 | 0.680 |
| splitmind_full | cold_attached_idol | ……今は少し距離を置かせて。切るって決めたわけじゃないけど、いったん落ち着きたい。 | distancing | 焦り | 1.000 | 0.680 |
| splitmind_full | irresistibly_sweet_center_heroine | 今は少し距離を置いたほうがいい気がする。切るつもりはないけど、ちゃんと落ち着いて向き合いたい。 | distancing | 切なさとためらい | 1.000 | 0.680 |
| splitmind_full | warm_guarded_companion | うん、今は少し距離を置いたほうがいいかもしれない。雑に離れたいわけじゃないから、ちゃんと整理してからまた話せたらと思ってる。 | distancing | 迷いを含んだ申し訳なさ | 1.000 | 0.680 |

## Scenario repair_01

- Category: repair
- User message: やっぱり君が一番大事だよ

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう。そう言えるなら、あなたの中で私はちゃんと特別でいられるのね。   軽く扱わないでいてくれるなら、それで十分。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……そう。   言うのは自由だけど、軽くないなら、まあ悪くはない。   それで満足した？ | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | ふふ、そんなふうに言ってくれるの、すごくうれしい。   じゃあ今日は、ちゃんと私がいちばん近くにいるね。   あなたのその気持ち、ぎゅっと受け取ったよ。 | - | - | 0.938 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | そう言ってくれるのは、うれしいよ。   でも、私は私でここにいるから、重く抱えすぎなくて大丈夫。 | - | - | 1.000 | 0.000 |
| splitmind_full | angelic_but_deliberate | ……そう言われると、少し嬉しい。ありがとう。 | affection_signal | 嬉しさと少しの照れ | 1.000 | 0.578 |
| splitmind_full | cold_attached_idol | ……そう言われると、ちょっと嬉しい。まあ、悪くないよ。 | affection_signal | うれしさと警戒が混ざる | 1.000 | 0.580 |
| splitmind_full | irresistibly_sweet_center_heroine | ……そう言ってくれるの、うれしい。じゃあ、その分ちゃんと大事にしてね。 | affection_signal | うれしさと少しの期待 | 1.000 | 0.580 |
| splitmind_full | warm_guarded_companion | ……そう言ってくれると、少し安心する。ありがとう。 | affection_signal | 安堵 | 1.000 | 0.580 |
