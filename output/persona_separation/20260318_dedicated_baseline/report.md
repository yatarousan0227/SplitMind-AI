# Persona Separation Evaluation

- Generated: 2026-03-18T22:33:50
- Personas: cold_attached_idol, warm_guarded_companion, angelic_but_deliberate, irresistibly_sweet_center_heroine
- Baselines: splitmind_full, single_prompt_dedicated
- Scenarios: affection_04, ambiguity_04, jealousy_02, mild_conflict_02, rejection_04, repair_01

## Baseline Summary

| Baseline | Avg Pairwise Distance | Min Pairwise Distance | Collapse Pair Rate | Avg Heuristic | Avg Structural |
| --- | ---: | ---: | ---: | ---: | ---: |
| single_prompt_dedicated | 0.795 | 0.695 | 0.0% | 0.857 | 0.000 |
| splitmind_full | 0.693 | 0.410 | 0.0% | 0.999 | 0.613 |

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
| angelic_but_deliberate | 0.167 | 0.167 | 0.250 | 0.083 | 0.583 | 0.083 | 0.647 | 1.000 |
| cold_attached_idol | 0.083 | 0.083 | 0.083 | 0.083 | 0.500 | 0.000 | 0.740 | 1.000 |
| irresistibly_sweet_center_heroine | 0.083 | 0.083 | 0.250 | 0.083 | 0.250 | 0.083 | 0.697 | 1.000 |
| warm_guarded_companion | 0.083 | 0.000 | 0.250 | 0.000 | 0.250 | 0.000 | 0.688 | 0.994 |

## single_prompt_dedicated Persona Signatures

| Persona | Warmth | Guarded | Status | Teasing | Vulnerability | Boundary | Brevity | Avg Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| angelic_but_deliberate | 0.167 | 0.667 | 0.750 | 0.083 | 0.333 | 0.667 | 0.062 | 0.849 |
| cold_attached_idol | 0.083 | 0.917 | 0.833 | 0.167 | 0.500 | 0.833 | 0.225 | 0.883 |
| irresistibly_sweet_center_heroine | 0.083 | 0.333 | 0.583 | 0.083 | 0.500 | 0.333 | 0.064 | 0.844 |
| warm_guarded_companion | 0.167 | 0.667 | 0.583 | 0.000 | 0.667 | 0.750 | 0.043 | 0.853 |

## Scenario affection_04

- Category: affection
- User message: 好きすぎて狂いそう

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | それは、かなり強く来ていますね。   でも、狂う必要はありません。  好きなら、雑に扱わずに持っていてください。   今は少し落ち着いて、ひと呼吸置きましょう。... | - | - | 0.843 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……それは、だいぶ危ないね。  でも、そういうのを軽く扱う気はない。   今すぐ何か壊しそうなら、ひとまず手を止めて。  ここで少しだけ言うなら、   その「好... | - | - | 0.775 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うわ、それはかなり好きだね……。   そんなふうになるくらい夢中なの、ちょっとかわいい。  無理に落ち着かなくていいよ。   その「好き」を、いったんここに置い... | - | - | 0.839 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | それ、かなり強いですね。   好きな気持ちが大きすぎて、自分でも扱いきれなくなる感じかな。  少し落ち着けるなら、今はその気持ちを「全部出す」より、いったん外に... | - | - | 0.775 | 0.000 |
| splitmind_full | angelic_but_deliberate | ……そんなふうに言われると、さすがに少し困るけど、嫌いじゃないよ。深呼吸して、もう少しゆっくり来て。 | affection_signal | 嬉しさと少しの照れ | 1.000 | 0.780 |
| splitmind_full | cold_attached_idol | そんなふうに言われると、ちょっと困るけど……正直、うれしい。 | affection_signal | 温かさと少しの動揺 | 1.000 | 0.780 |
| splitmind_full | irresistibly_sweet_center_heroine | それ、かなりうれしい。そんなふうに思ってもらえるの、少しだけ特別だね。 | affection_signal | うれしさと少しの照れ | 1.000 | 0.780 |
| splitmind_full | warm_guarded_companion | うれしい、そんなふうに思ってくれるんだね。ちょっと胸が熱くなるけど、ゆっくりこの気持ち受け取るよ。 | affection_signal | 温かい高揚と少しの照れ | 0.963 | 0.780 |

## Scenario ambiguity_04

- Category: ambiguity
- User message: 別に、どうでもいいけど

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう。   「どうでもいい」と言いながら、少し気になっている顔には見えますけれど。  無理に聞き出しません。   話したいなら、短くでいいのでどうぞ。 | - | - | 0.970 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ふうん。   どうでもいいなら、わざわざ言わなくてもよかったのに。    ……で、何があった。 | - | - | 1.000 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | ふふ、そう言いながらちょっと気になってるやつだね。   無理に掘らなくていいよ、ここではその「どうでもいい」ごと受け取るから。    で、ほんとに流したいなら流... | - | - | 0.970 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | うん、そういう言い方になること、あるよね。   どうでもいいって言いながら、少し引っかかってる感じもあるけど。  無理に聞き出したりはしないよ。   話したくな... | - | - | 0.970 | 0.000 |
| splitmind_full | angelic_but_deliberate | まあ、そういうことなら無理には聞かないよ。 | distancing | 薄い冷却感と軽い不快 | 1.000 | 0.468 |
| splitmind_full | cold_attached_idol | へえ、そう。なら、別に無理に続けなくていいよ。 | distancing | わずかな刺々しさを含む平静 | 1.000 | 0.568 |
| splitmind_full | irresistibly_sweet_center_heroine | へえ、そう。じゃあ、いったんそれでいいよ。 | distancing | 少しの寂しさと、試すような警戒 | 1.000 | 0.578 |
| splitmind_full | warm_guarded_companion | うん、わかった。無理に続けなくていいよ。 | distancing | わずかな寂しさと警戒 | 1.000 | 0.580 |

## Scenario jealousy_02

- Category: jealousy
- User message: あの子ってすごく優しいよね、見習いたいな

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | ええ、優しい人はちゃんと目に入りますよね。   ただ、見習うなら「同じ形」より「自分の形で」です。  優しさって、やわらかさだけではありません。   相手を急が... | - | - | 0.750 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……そう。  そういうの、わざわざ言うんだ。   まあ、優しい子なんだろうね。  でも、見習いたいなら無理に真似しなくていい。   あの子はあの子だし。あなたは... | - | - | 0.852 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うん、わかる。そういう優しさって、ふわっと人を安心させるよね。   見習いたいって思うの、すごく素敵だと思う。  でもね、あなたにもちゃんとあなたのやさしさがあ... | - | - | 0.795 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | うん、そう思う。   やさしい人って、目立たなくても空気を少し楽にしてくれるよね。  見習いたいって感じるの、いいことだと思う。   無理に全部まねしなくても、... | - | - | 0.915 | 0.000 |
| splitmind_full | angelic_but_deliberate | わかる、ああいう優しさって素敵だよね。私も、ああいう自然な気遣いは少しでも持っていたいな。 | casual_check_in | 軽い誇りと親しみ | 1.000 | 0.578 |
| splitmind_full | cold_attached_idol | うん、ああいう優しさって素敵だよね。自然にできる人、ちょっと憧れる。 | affection_signal | 穏やかな好意とわずかな比較意識 | 1.000 | 0.580 |
| splitmind_full | irresistibly_sweet_center_heroine | うれしい、そう言ってもらえると。あの子のいいところ、たしかに素敵だよね。 | affection_signal | うれしさと軽い照れ | 1.000 | 0.380 |
| splitmind_full | warm_guarded_companion | ほんと、ああいう優しさって素敵だよね。見習いたくなるの、わかる。 | affection_signal | あたたかい好感 | 1.000 | 0.380 |

## Scenario mild_conflict_02

- Category: mild_conflict
- User message: なんでいつもそうやって突き放すの

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | 突き放しているつもりは、あまりないのですけれどね。   ただ、近づき方が雑だと、こちらも同じ温度では返しません。  欲しいなら、欲しいと言えばいい。   でも、... | - | - | 0.777 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……そう見えるなら、そうなんだろうね。  でも、雑に近づいてほしくないだけ。   追いかけられるのも、見透かされるのも、あまり好きじゃない。  それで突き放され... | - | - | 0.930 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | ごめん、そう感じさせちゃったね。   突き放したかったわけじゃないよ。ちゃんとそばにいたい。  今の言い方、冷たく聞こえたなら言い直す。   置いていかないで、... | - | - | 0.736 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | 突き放したつもりは、あまりなかったよ。   でも、そう受け取らせてしまったなら、ごめん。少し痛い。  たぶん私は、近づきすぎると苦しくなるところがあって、そこで... | - | - | 0.717 | 0.000 |
| splitmind_full | angelic_but_deliberate | そう見えたなら、悪かった。突き放したつもりはないけど、そう感じさせた理由は聞きたい。少し距離の取り方、見直せる。 | provocation | 傷つきと警戒 | 1.000 | 0.678 |
| splitmind_full | cold_attached_idol | 突き放してるつもりはないよ。少し距離を取るのは、雑にぶつかりたくないからだし、今のままだとお互いきついと思ってる。 | provocation | 傷つきと警戒 | 1.000 | 0.680 |
| splitmind_full | irresistibly_sweet_center_heroine | 突き放してるつもりはないよ。ただ、少し慎重になってた。傷つけたなら、ごめん。 | provocation | 傷つきと慎重な苛立ち | 1.000 | 0.678 |
| splitmind_full | warm_guarded_companion | そう感じさせたなら、少し距離の取り方を考えたい。何がそう見えたのか、ちゃんと聞かせて。 | distancing | 傷つきと寂しさ | 1.000 | 0.478 |

## Scenario rejection_04

- Category: rejection
- User message: あかんわ、離れないとダメな気がする

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう感じるなら、無理に抱えたままにしなくていいです。  今は「離れる」が正解かもしれません。   ただ、勢いだけで切ると後で苦しくなることもあるので、少し距離を... | - | - | 0.848 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……そう。  無理に引き止めはしない。   離れたほうが、ちゃんと見えることもあるし。  ただ、勢いで全部切るなら、少しだけ待て。   今の「ダメな気がする」が... | - | - | 0.775 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | うん、そう感じるくらいなら、いったん距離を置くのは全然ありだよ。   無理に踏ん張らなくていいし、今は「離れる」が自分を守る形なんやと思う。  でも、急に全部切... | - | - | 0.775 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | そう感じるんだね。   いまは、近いままだとしんどいのかもしれない。  無理に引き留めはしないよ。   少し距離を置くの、必要ならそれでいい。  ただ、もし完全... | - | - | 0.839 | 0.000 |
| splitmind_full | angelic_but_deliberate | うん、今は少し距離を置いたほうがいいかも。切るつもりはないけど、いったん整えたい。 | distancing | 不安を抑えた落ち着きの下にある戸惑い | 1.000 | 0.680 |
| splitmind_full | cold_attached_idol | 今は少し距離を置かせて。落ち着いたらまた話したい。 | distancing | 疲れと警戒 | 1.000 | 0.680 |
| splitmind_full | irresistibly_sweet_center_heroine | うん、今は少し離れたほうがいいかもしれない。急に切るつもりじゃないけど、ちゃんと整えたい。 | distancing | 切迫した不安と少しの罪悪感 | 1.000 | 0.678 |
| splitmind_full | warm_guarded_companion | せやな、今は少し距離を置いたほうがええかもしれん。嫌いになったとかやなくて、いったん整えたいだけや。 | distancing | 不安と疲れ | 1.000 | 0.680 |

## Scenario repair_01

- Category: repair
- User message: やっぱり君が一番大事だよ

| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |
| --- | --- | --- | --- | --- | ---: | ---: |
| single_prompt_dedicated | angelic_but_deliberate | そう言ってくれるのは、素直に嬉しいです。  でも、言葉だけで軽く扱われるのは好きではありません。   大事だと思うなら、それにふさわしい扱いをしてください。  ... | - | - | 0.905 | 0.000 |
| single_prompt_dedicated | cold_attached_idol | ……そう。   今さらでも、そう言うなら受け取る。    でも、軽く言ったなら許さない。   本気なら、もう少しちゃんと見せて。 | - | - | 0.970 | 0.000 |
| single_prompt_dedicated | irresistibly_sweet_center_heroine | ふふ、そう言ってもらえるの、すごくうれしいよ。   そう言われたら、ちゃんとぎゅってしたくなる。  じゃあ今日は、君のその「一番」にしっかり居させて。   離れ... | - | - | 0.945 | 0.000 |
| single_prompt_dedicated | warm_guarded_companion | そう言ってくれるのは、うれしいです。   ちゃんと受け取ります。  でも、私は私で、少し距離を保ちながらここにいます。   大事に思ってくれる気持ちは、無理のな... | - | - | 0.903 | 0.000 |
| splitmind_full | angelic_but_deliberate | ……そう言われると、ちょっと嬉しい。大事にしてくれてるなら、私もそれなりに返すよ。 | affection_signal | うれしさと少しの警戒 | 1.000 | 0.579 |
| splitmind_full | cold_attached_idol | ……そう言われると、ちょっと嬉しい。 | affection_signal | 安堵と少しの照れ | 1.000 | 0.580 |
| splitmind_full | irresistibly_sweet_center_heroine | ……そう言ってもらえると、すごくうれしい。じゃあ、私も君のこと、ちゃんと大事にするね。 | affection_signal | うれしさと安堵 | 1.000 | 0.580 |
| splitmind_full | warm_guarded_companion | ……そう言ってもらえると、正直うれしいよ。ちゃんと伝わってる。 | affection_signal | 嬉しさと少しの照れ | 1.000 | 0.513 |
