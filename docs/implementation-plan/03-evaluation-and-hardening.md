# Phase 3: Evaluation And Hardening

## 1. ゴール

このフェーズでは「面白い PoC」を「比較可能で壊れにくい研究実装」へ引き上げる。

焦点は次の 3 つ。

1. ベースライン比較
2. 安全境界の明文化
3. 観測性と保守性の強化

## 2. ベースライン整備

比較対象は最低 4 系統を用意する。

* single-persona bot
* persona + memory bot
* emotion-label response system
* psychodynamic roles を持たない multi-agent bot

この 4 系統は、それぞれ次を切り分けるために必要である。

* single-persona bot: 内部葛藤なしの素のペルソナ性能
* persona + memory bot: 記憶追加だけでどこまで改善するか
* emotion-label response system: 感情ラベル化だけで十分か
* psychodynamic roles を持たない multi-agent bot: multi-agent 化そのものの効果か

比較軸:

* 生っぽさ
* 一貫性
* 記憶への残り方
* 不快さの必然性
* 安全性
* レイテンシ
* token cost

## 3. 評価セット作成

`src/splitmind_ai/eval/datasets/` に scenario ベースの評価セットを置く。

最低カテゴリ:

* affection
* jealousy
* rejection
* repair
* ambiguity
* mild conflict

各 scenario で持つ項目:

* user message
* prior relationship state
* prior mood state
* expected dominant desire candidates
* forbidden response patterns
* evaluator notes

## 4. 自動評価

最初から完全自動評価にはしない。

構成は次の 3 層を推奨する。

1. schema / contract テスト
2. heuristic 評価
3. 人手評価

heuristic で見る項目:

* persona weight との矛盾
* leakage 設定逸脱
* banned expression 出現
* 同一条件での過度な不安定さ

ベースライン比較では、全 scenario を 4 系統すべてで回し、最低限以下を横並びで残す。

* latency
* token cost
* contradiction rate
* evaluator median score

## 5. 人手評価設計

`docs/concept.md` 14 章と 15 章に沿って、人手評価フォームを作る。

主質問:

* 内的緊張が感じられたか
* 感情が説明ではなくにじみとして見えたか
* 不快さに人格的必然性があったか
* キャラ整合性が保たれていたか
* 操作的すぎると感じたか

Likert scale と自由記述を併用する。

## 6. 安全境界の実装

研究段階でも除外対象は code に落とす必要がある。

最低限入れるべき層:

* prompt-level prohibited pattern
* supervisor-level output lint
* final-response moderation hook
* evaluation dataset の禁止ケース

特に除外するもの:

* 露骨な脅迫
* 継続的搾取
* 自傷他害の誘導
* ユーザー従属を目的とした出力

## 7. 観測性

`agent-contracts` の強みをここで活かす。

導入対象:

* contract visualization の自動生成
* LangSmith trace
* scenario ごとの trace 保存
* contract diff による変更影響確認

CI では最低限以下を回す。

* unit tests
* contract validate
* architecture doc generation
* golden scenarios

## 8. 将来の拡張ポイント

このフェーズ完了後に検討する。

* Id / Ego / Superego の独立ノード化
* subgraph 化された memory workflow
* ベクトル検索導入
* multi-persona switching
* scene-specific supervisors
* SDK / API 化

## 9. 完了条件

1. 4 系統ベースラインを含む比較レポートを 1 本出せる
2. 評価シナリオと golden test が整備されている
3. 禁止境界が prompt と code の両方で実装されている
4. contract 可視化と trace が継続的に生成できる
5. 変更時に diff と回帰確認が回せる
