# 09 — 人間らしい雑味のための生成アーキテクチャ再設計

## 1. 目的

実装順は [`09-implementation-tasklist.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/09-implementation-tasklist.md) を参照。

2026-03-18 時点の SplitMind-AI は、

- 感情の漏れ
- 境界線
- 追いたくなる余白

はかなり再現できている。

一方で、レビューで指摘された通り、最終文面にはまだ次の AI 臭さが残る。

- 毎ターン少し決め台詞すぎる
- 揺れ方の種類が少なく、均質
- 説明ターンが続くと「設定資料を喋る AI」になる
- 関係の進展が早い場面で、承認がきれいに成立しすぎる

本ドキュメントでは、現行実装を踏まえて、
「感情の漏れ」自体ではなく、
**漏れた感情がどのくらい雑に、ためらいながら、関係段階に応じて出るか**
を改善する。

ただしこの Phase では、
prompt の微調整や表現の小手先の散らしを中心にはしない。
目標は
**生成アーキテクチャそのものを、きれいな完成文を作る系から、人間らしい揺れを残せる系へ組み替えること**
である。

---

## 1.1 この Phase の立場

この Phase は最適化ではない。

- 単なる prompt 改良フェーズではない
- 語尾や言い淀みの追加で済ませるフェーズではない
- latency 維持を最優先するフェーズでもない

これは
**「内部では揺れているのに、最後に均整の取れた返答へ圧縮される」**
という現在の生成構造に対する根本対応である。

したがって、必要なら次を受け入れる。

- pass 数の増加
- state slice の追加
- contract の拡張
- node 責務の再分割
- eval 指標の再設計

---

## 2. レビュー指摘の要約

今回のレビューは、単に「もっと人間らしく」ではなく、かなり具体的である。

### すでに良い点

- すぐ落ちない
- でも拒絶しすぎない
- 相手に次の一手を出させる余白がある
- 肯定しつつ、全部は渡さない

### 改善が必要な点

- 文面が毎回きれいに整いすぎる
- 文体の癖が固定されている
- 好意への返しがうまくまとまりすぎる
- 価値観説明が連続すると説明臭くなる
- 関係進行の承認が一段早い

要するに、今の問題は
**「感情が出ていない」ではなく、「感情が上手に出すぎている」**
ことである。

---

## 3. 現状調査

この問題は単一箇所ではなく、現在の 2-pass 寄り runtime 全体で起きている。

なお本 Phase では、
**速度維持は最優先ではない**。
必要なら call 数やモデル構成を見直してもよく、
判断基準は first-token latency ではなく
**最終文面の人間らしさと関係進行の自然さ**
を優先する。

### 3.1 `PersonaSupervisorNode` が実質的に最終文面を確定している

現状の `PersonaSupervisorNode` は、
frame 生成と候補選択を 1 回の structured output でまとめて返している。

参照:

- `src/splitmind_ai/nodes/persona_supervisor.py`
- `src/splitmind_ai/prompts/persona_supervisor.py`
- `docs/implementation-plan/07-performance-tension-and-response-length.md`

特に `PersonaSupervisorNode` はその場で `response.final_response_text` を書き込むため、
通常フローでは後段の `SurfaceRealizationNode` が発火しにくい。

これは速度には効くが、次の副作用がある。

- 候補比較が「本当に別の候補を比べる工程」ではなくなりやすい
- LLM が最初から 1 本の完成形を作り、その周辺に似た候補を添えるだけになりやすい
- 「少し不格好だが生っぽい候補」を後段で拾い直す余地が減る

つまり、レビューで言う
「全部が綺麗に返りすぎ」
を構造的に助長している。

ここで重要なのは、
これは prompt の表現不足ではなく
**生成責務の潰し込み方そのもの**
に由来する点である。

### 3.2 候補の差分軸が粗い

`UtterancePlannerNode` 自体は複数 blueprint を作るが、差分は主に以下に寄っている。

- `mode`
- `opening_style`
- `interpersonal_move`
- `latent_signal`
- `length`

参照:

- `src/splitmind_ai/nodes/utterance_planner.py`
- `src/splitmind_ai/contracts/persona.py`

しかし、人間らしい雑味を作るのに必要なのは、
`tease / probe / withdraw` のような大分類だけでは足りない。
必要なのは例えば次のような微差である。

- 少し照れて短くなる
- 刺したあとで少し引く
- 嬉しいのに茶化す
- 価値観を語らず、質問だけ返す
- 本当は受け取りたいが、一回だけ保留する

現行 contract にはこうした
**微細な会話姿勢の軸**
がない。

つまり SplitMind-AI は、
「どの行動を取るか」は持っているが、
「その行動をどんな生っぽい崩れ方で出すか」を state として持っていない。

### 3.3 「最近どんな返し方をしたか」を覚えていない

現状の state には関係・ムード・drive・active theme はあるが、
**直近数ターンでどんな表出パターンを使ったか**
を抑制する仕組みがない。

そのため、

- `へえ`
- `ふーん`
- `……で`
- 短い牽制
- 価値観の一言

のような marker が、局所的には良くても数ターン並ぶとテンプレに見える。

`eval/heuristic.py` には response set diversity の土台があるが、
これは同一 intent の複数応答比較用であり、会話中の turn-to-turn 再利用をまだ見ていない。

参照:

- `src/splitmind_ai/eval/heuristic.py`

### 3.4 評価が「整いすぎ」を十分に罰していない

現在の heuristic は優秀で、

- direct emotion naming
- counselorish drift
- believability
- anti-exposition
- same-intent diversity

は見ている。

ただし、今回のレビューで問題になっているのは、もう少し別の層である。

- 毎ターン名台詞化していないか
- 文体マーカーが近接ターンで再利用されていないか
- 価値観の言語化が続きすぎていないか
- 関係の進展が現在の会話熱量に対して早すぎないか

この層の罰則がないため、
「安全で、人格もあり、でも上手すぎる」
応答が通ってしまう。

### 3.5 関係進行の段階制御が弱い

`ActionArbitrationNode` は appraisal と drive から mode を選ぶが、
**告白・半承認・保留・試し行動**
のような関係進行の段階管理を持っていない。

参照:

- `src/splitmind_ai/nodes/action_arbitration.py`
- `src/splitmind_ai/contracts/action_policy.py`

そのため、たとえば「付き合おう」に対して

- うれしさが漏れる
- でも即承認までは行かない
- もう一段試す

という恋愛会話特有の pacing を、
drive だけで安定再現するのが難しい。

---

## 4. 根本原因の整理

今回の問題は、次の 4 つに整理できる。

### 原因 A: 漏れの設計はあるが、揺れの設計が弱い

`leakage_level`, `hesitation`, `unevenness`, `rupture_points` は存在する。
ただしそれが

- どの turn で
- どの種類の崩れ方として
- どのくらいの密度で

出るかは粗い。

結果として、
「少し漏れる」は実現しても、
「今回は照れ」「今回は茶化し」「今回は短すぎる返し」「今回は一歩引く」
のような **揺れのローテーション** にならない。

### 原因 B: 候補生成が mode 中心で、surface posture を持たない

今の候補差分は social action の違いとしては自然だが、
文面の肌触りを変えるには不足している。

必要なのは `mode` に加えて、
**その turn の表出姿勢**
を独立に持つこと。

### 原因 C: 「完成度の高い 1 本」を選びやすい

プロンプトでは「整いすぎた文より引っかかる文を選ぶ」と書いてある。
ただ、候補比較の実効性が弱い状態では、
LLM は依然として「一番うまい 1 本」を作りやすい。

これは言い換えると、
現在のシステムの暗黙の目的関数が
**「そのターンで最も完成度の高い返答を返す」**
になっているということでもある。

### 原因 D: 関係段階の gate がない

恋愛会話で自然に見えるかは、内容だけでなく
**その段階でそこまで言うか**
に強く依存する。

今はこの gate が薄いため、レビューで指摘された
「展開が少し早い」
が起きやすい。

---

## 5. この Phase が根本対応として変えるもの

この Phase では、次の前提を捨てる。

- 「内部の揺れは prompt で漏らせば十分」
- 「mode があれば表面の自然さも担保できる」
- 「候補は 2-3 本あれば比較工程として十分」
- 「恋愛会話の pace は appraisal と drive の組み合わせで足りる」

代わりに、次を新しい中核原理とする。

1. 人間らしさは文体ではなく、surface state の推移として扱う
2. 最終文面は 1 回のきれいな統合で決めず、比較可能な複数姿勢から選ぶ
3. 1 ターン単体ではなく、近接ターン列として自然さを評価する
4. 関係進行は独立した状態機械として扱う

---

## 6. 改善方針

改善は次の 5 track に分ける。

優先度は上から高い。

### Track 1: Surface Posture を contract 化する

#### 目的

`selected_mode` とは別に、
その turn の **話し方の姿勢** を明示する。

#### 提案

`ExpressionSettings` もしくは `PersonaSupervisorFrame` に、
次のような surface posture 系フィールドを追加する。

```python
surface_posture: str
# 例:
# - clipped_guard
# - embarrassed_short
# - teasing_cover
# - cool_reach
# - half_pullback
# - plain_accept
# - values_drop
# - question_return

ornamentation_budget: float
# 0.0 に近いほど名台詞化を抑え、平文で返す

initiative_balance: float
# 0.0 = 受け中心, 1.0 = 主導中心

admission_level: float
# 0.0 = ほぼ認めない, 1.0 = かなり認める

closure_level: float
# 0.0 = 会話を開く, 1.0 = 切る
```

#### 狙い

例えば同じ `probe` でも、

- `question_return`
- `teasing_cover`
- `half_pullback`

では人間の印象がかなり違う。

この軸がない限り、
`mode` を変えても「似たような賢い返し」に寄りやすい。

この track は prompt 改良ではなく、
**表出を state 化するための土台**
である。

### Track 2: Turn 単位のローテーション制御を入れる

#### 目的

毎ターン同じ美点を全部出さないようにする。

#### 提案

`working_memory` か新しい state slice に、
直近 3-5 ターンの surface history を保存する。

保持候補:

- opener marker
- surface_posture
- 質問で終えたか
- 価値観を語ったか
- 喜び/照れ/刺し/引き のどれが主だったか
- relation-escalation を進めたか

その上で次 turn では以下を抑制する。

- 同じ opener の連続
- 価値観説明の連続
- 「刺してから質問」の連続
- きれいな二段落ちの連続

#### 実装イメージ

Python 側で軽い penalty を入れるだけでも効く。

- 同 posture を 2 連続で -0.15
- `values_drop` を 3 ターン中 2 回以上で -0.20
- opener marker 再利用で rerank penalty

ただし本質は penalty そのものではなく、
**表出履歴を model 外の状態として保持すること**
にある。

### Track 3: 候補比較を本当に機能させる

#### 目的

「一番うまい 1 本」ではなく、
「少し荒いが今の熱量に合う 1 本」を選べるようにする。

#### 推奨案

品質優先で、生成責務を再分離する。

1. `PersonaSupervisorNode`
   - final text を返さない
   - frame と `surface_posture options` と `selection_criteria` のみ返す
2. `UtterancePlannerNode`
   - Python 側で posture 差分を明確に持つ 3-5 候補を組む
3. `SurfaceRealizationNode`
   - 候補の実現と選択だけを担当する
4. 必要なら `SelectionCriticNode`
   - 近接ターン履歴と relationship pacing を見て rerank する

#### 候補の差分ルール

候補は最低でも次の 2 軸以上を変える。

- openness
- roughness
- initiative
- warmth leak
- relation pacing

例:

- 候補 A: 短く照れる
- 候補 B: 少し試す
- 候補 C: 平たく受けて質問を返す
- 候補 D: 一度だけ引く
- 候補 E: 価値観は出さず、確認だけする

#### なぜこれが根本対応か

問題は「候補が少ない」ことではなく、
**最終文面の決定が早すぎること**
である。

したがって根本対応は、
候補表面の言い回しを増やすことではなく、
`決定の遅延` と `比較責務の独立`
を取り戻すことになる。

#### 代替案

もし runtime の簡潔さを残したいなら、
combined path は残しつつ、出力候補に対して Python 側で

- opener reuse
- marker reuse
- posture reuse
- ornamentation overuse

の diversity lint をかけ、似すぎたら 1 回だけ再生成する。

ただしこれは fallback であり、本命ではない。
本件では quality first なので、
迷ったらこの代替案ではなく
**`frame -> planner -> realization -> critic`**
へ寄せた方がよい。

### Track 4: 関係進行の pace gate を追加する

#### 目的

「嬉しい」は漏れるが、「成立」はまだ早い、を制御する。

#### 提案

`relationship` または新 slice に、会話進行用の指標を持つ。

```python
relationship_stage: str
# unfamiliar | warming | charged | testing | mutual

commitment_readiness: float
confession_credit: float
repair_depth: float
```

#### 使用ルール

- `relationship_stage < testing` では即承認を基本禁止
- `commitment_readiness < 0.65` なら
  - engage を full_accept にしない
  - probe / tease / soften へ寄せる
- 告白系発話には
  - 喜びの漏れ
  - 継続意思の確認
  - もう一段の試し
  の順で返す

#### 期待効果

レビューの
「Turn 7 はかなり良いが、もう少し嬉しさを漏らしつつ、まだ一段試したい」
を設計として再現しやすくなる。

### Track 5: 評価軸を拡張する

#### 目的

「悪くないが上手すぎる」応答を落とせるようにする。

#### 追加したい heuristic

1. `turn_local_opener_reuse`
   - 近接ターンで opener が再利用されすぎていないか

2. `ornamentation_density`
   - 毎ターン比喩的・名台詞的な締めが入っていないか

3. `values_exposition_streak`
   - 価値観説明ターンが連続していないか

4. `question_return_balance`
   - 相手に返す turn が不足していないか

5. `relationship_pacing`
   - 会話量に対して承認・告白受理・深い開示が早すぎないか

6. `roughness_presence`
   - 短さ、言いよどみ、平文、少し雑な切り方が一定割合であるか

#### dataset 追加案

既存カテゴリに加えて、次を eval 用に追加する。

- `courtship_escalation.yaml`
- `overeager_confession.yaml`
- `distance_threat_but_not_terminal.yaml`
- `affection_with_embarrassment.yaml`

---

## 7. Streamlit ダッシュボード/UI 更新も Phase 9 の対象に含める

これは必要である。

理由は単純で、Phase 9 で追加する中核要素の多くが
**現状の Dashboard に出ていない**
からである。

現行 Dashboard が主に可視化しているのは次の層である。

- relationship
- mood
- drive
- appraisal
- self_state
- conversation_policy
- leakage / containment
- node timing

参照:

- `src/splitmind_ai/ui/dashboard.py`
- `src/splitmind_ai/ui/app.py`

しかし Phase 9 の主題は次であり、これは現状 UI からほぼ見えない。

- `surface_posture`
- `ornamentation_budget`
- `initiative_balance`
- `admission_level`
- `closure_level`
- `recent_surface_history`
- `relationship_stage`
- `commitment_readiness`
- `confession_credit`
- 候補間の posture 差分
- `SelectionCriticNode` が何を理由に候補を落としたか

この状態で backend だけ更新すると、
実装は進んでも「本当に均整化が減ったか」「進展が早すぎる問題が改善したか」を
定性検証できない。

したがって Phase 9 では、
**Dashboard を研究 UI として再設計すること**
を正式に含める。

### UI で新たに観測すべき項目

1. Surface State
   - current posture
   - ornamentation budget
   - initiative balance
   - admission level
   - closure level

2. Surface History
   - 直近 3-5 turn の opener
   - 直近 3-5 turn の posture
   - values_drop / question_return / tease_cover の履歴
   - 再利用ペナルティが発火したか

3. Relationship Pacing
   - relationship_stage
   - commitment_readiness
   - confession_credit
   - 今 turn で escalation が許可されたか blocked されたか

4. Candidate Comparison
   - 候補ごとの posture
   - 候補ごとの pacing risk
   - critic による rejection reason
   - selected candidate と次点候補の差分

5. Quality Diagnostics
   - opener reuse warning
   - ornamentation density warning
   - values exposition streak
   - pacing violation warning

### 期待する UI 変更

- `build_turn_snapshot()` に Phase 9 の state を含める
- `build_current_dashboard()` に surface / pacing / critic の view-model を追加する
- trace panel に `SurfaceStateNode` と `SelectionCriticNode` の出力を追加する
- candidate chart を policy score だけでなく posture / pacing risk / critic verdict も見える形に拡張する
- history chart に surface posture と relationship stage の推移を追加する

### 位置づけ

これは装飾ではない。

Phase 7 では timing 可視化が runtime 改善のための観測装置だった。
同様に Phase 9 では、
Dashboard が
**「人間らしい雑味が state と選択に乗っているか」を検証するための観測装置**
になる。

したがって UI 更新は後回しの周辺タスクではなく、
Phase 9 本体に含める。

---

## 8. レビュー指摘との対応表

| レビュー指摘 | 現状原因 | 改善 track |
|---|---|---|
| 毎ターン決め台詞っぽい | ornamentation 制御なし、履歴 penalty なし | Track 1, 2, 5 |
| 揺れ幅が均質 | posture 軸なし | Track 1, 3 |
| 「好き」への返しがテンプレ | candidate 差分が粗い | Track 1, 3 |
| turn 4-6 が説明的 | values/exposition streak を見ていない | Track 2, 5 |
| turn 7 の進展が少し早い | relationship pacing gate なし | Track 4 |
| AI として均整の取れた返答になる | combined path で完成形を作りやすい | Track 3 |

---

## 9. 根本対応と対症療法の線引き

この Phase では、以下を明確に分けて扱う。

### 根本対応

- `surface_posture` を contract / state に入れる
- `recent_surface_history` を state に入れる
- `PersonaSupervisor` から final text 決定責務を外す
- `frame -> planner -> realization` を分離する
- `relationship_pacing` を独立 slice として導入する
- eval を turn 単体から近接ターン列へ拡張する

### 対症療法

- prompt に「自然にして」を足す
- 語尾や間投詞を少し増やす
- opener をランダムに散らす
- 直接表現をさらに禁止する
- モデルだけを小さく or 別のものに替える

この Phase では、対症療法は否定しないが、主戦略にしない。

---

## 10. 優先実装順

最小コストで効く順は次の通り。

### Step 1

`surface state` を先に入れる。

- `surface_posture`
- `ornamentation_budget`
- `initiative_balance`
- `admission_level`
- `closure_level`

### Step 2

`surface history` を state に入れる。

- opener
- posture
- question_return
- values_drop

の 4 つだけでもよい。

### Step 3

`PersonaSupervisorNode` から final text 決定を外す。

- combined path を主経路にしない
- supervisor は frame と posture option だけ返す
- final text は後段で比較して決める

### Step 4

candidate 比較を再実装する。

本件では 2-call 維持にこだわらず、
planner / realization の実効性を戻す方を優先する。
必要なら critic も足す。
model は小さくしてよいが、比較工程そのものは削らない。

### Step 5

`relationship pacing` を独立状態として入れる。

- `relationship_stage`
- `commitment_readiness`
- `confession_credit`

を導入し、恋愛会話の承認速度を state で制御する。

### Step 6

最後に eval / prompt / Dashboard をその新構造に合わせて更新する。

- ornamentation / opener reuse / pacing の heuristic 追加
- prompt に「毎ターン名台詞を目指さない」を明文化
- plain / embarrassed / awkward な short reply を few-shot で増やす
- Streamlit Dashboard に surface / pacing / critic の可視化を追加する

---

## 11. アーキテクチャ変更案

推奨する target architecture は次。

1. `InternalDynamicsNode`
2. `MotivationalStateNode`
3. `SocialCueNode`
4. `AppraisalNode`
5. `ActionArbitrationNode`
6. `SurfaceStateNode` 新設
7. `PersonaSupervisorNode` 再定義
8. `UtterancePlannerNode` 強化
9. `SurfaceRealizationNode`
10. `SelectionCriticNode` 新設
11. `MemoryCommitNode`

### `SurfaceStateNode` の責務

- 直近 turn の表出履歴を読む
- 今 turn で使う `surface_posture` 候補を組む
- ornamentation / initiative / closure の予算を決める
- 近接ターンとの重複を避ける

### `PersonaSupervisorNode` の新責務

- internal state を `surface frame` に変換する
- 何を守るか、どこが崩れるかを定義する
- ただし本文は書かない

### `SelectionCriticNode` の責務

- 近接ターンとの重複を検査する
- relationship pacing に反していないか見る
- 一番うまい文ではなく、一番妥当な文を選ぶ

---

## 12. 具体的な prompt 修正案

追加したい指示は以下。

### supervisor / realization 共通

- 毎ターン、魅力・価値観・主導権・余白を全部入れようとしない
- 1 turn くらいは平文でよい
- うまい返しより、その場で反応した感じを優先する
- 喜びは「少し嬉しい」より、間・短文化・言い直しで出す
- 質問返しだけの turn を許容する
- 一度刺したら、その直後は少し引く候補も必ず作る

### 告白・好意受けの場面

- 嬉しさが漏れてもよい
- ただし成立を急がない
- 受理・保留・試し の 3 候補を必ず並べる

### 距離を置く宣言への応答

- 完全な突き放しを default にしない
- 「止めないが、勢いだけで決めるな」のような余白候補を含める

---

## 13. 成功条件

この改善が成功と言える条件は次の通り。

1. 3-5 ターン続けて見ても opener や文体マーカーの再利用が減る
2. 同じ persona でも、照れ・試し・平文・引き・質問返しがローテーションする
3. 好意や告白への返しで、嬉しさの漏れと pace control が両立する
4. 価値観説明が必要な turn 以外では、説明密度が下がる
5. 「上手いけど AI」ではなく、「少し崩れるけど人っぽい」に寄る
6. Dashboard 上で surface posture と relationship pacing の推移が観測できる
7. critic の rejection reason を turn ごとに追える

---

## 14. 推奨する次の実装単位

次に着手するなら、以下の順を推奨する。

1. `state` に `recent_surface_history` と `relationship_pacing` を追加
2. `contracts/persona.py` に `surface_posture` 系の field を追加
3. `SurfaceStateNode` を新設
4. `PersonaSupervisorNode` から final text 決定を外す
5. `UtterancePlannerNode` を posture-aware / pacing-aware にする
6. `SelectionCriticNode` を追加
7. `eval/heuristic.py` に `ornamentation_density`, `relationship_pacing`, `turn_local_opener_reuse` を追加
8. `ui/dashboard.py` と `ui/app.py` を Phase 9 state 可視化に対応させる

この順なら、表面の文体修正ではなく、
生成構造そのものから
「毎回上手く返しすぎる」
問題に手を入れられる。
