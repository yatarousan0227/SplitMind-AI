# Phase 7: Performance, Tension Decay, and Response-Length Control

## 1. 目的

Phase 6 までで、心理力動ベースの対話ループ自体は成立している。
一方で、実機 UI での定性確認から次の 3 問題が明確になった。

1. 1 ターンの応答が遅い
2. `tension` と `active_themes` が残留しやすい
3. 場面によっては返答が短すぎる

この Phase では、人格性を壊さずに対話体験を改善する。

## 2. 現状の問題整理

### 2.1 遅さ

現行パイプラインでは、1 ターンで少なくとも以下の 3 LLM ノードが直列に走る。

1. `InternalDynamicsNode`
2. `PersonaSupervisorNode`
3. `SurfaceRealizationNode`

さらに Streamlit UI では、各ターンで graph と LLM インスタンスを再構築している。
主因は 3 回の LLM call だが、UI 側の再構築も無視できない。

### 2.2 tension の残留

現行の state update は、緊張の加算に対して減衰が弱い。

- `jealousy_trigger` は `tension +0.07`
- `user_praised_third_party` は `tension +0.05`
- `reassurance_received` は `tension -0.03`
- `repair_attempt` は `tension -0.04`

また、`unresolved_tensions` は高圧ターンごとに追加または強化されるが、修復時の減衰は `-0.05` と小さい。
`working_memory.active_themes` も追加されるだけで、実質的な decay が存在しない。

### 2.3 応答長の偏り

`expression_settings.length` という contract は存在するが、実際の candidate 設計と realization prompt での拘束が弱い。
そのため、説明、修復、境界の再定義のような場面でも、短く切れすぎることがある。

## 3. この Phase の方針

### 3.1 守るもの

- persona 一貫性
- 冷たさと関心の両立
- 防衛と leakage の表現
- 安全境界

### 3.2 改善対象

- 体感レイテンシ
- 修復後の tension 回復速度
- 応答長の状況適応

## 4. 実装トラック

### 4.0 実行状況

2026-03-17 時点の状況は次の通り。

| Track | 状態 | 実施内容 | 残タスク |
|---|---|---|---|
| Track A | 実装済み | prompt / planner に `short / medium / long` の拘束を追加し、説明・修復系で短すぎる返答を抑制した | UI での定性再確認 |
| Track B | 実装済み | Streamlit runtime cache、node timing trace、Dashboard/Trace での timing 可視化、`persona_supervisor + surface_realization` の 2-pass 統合を追加した | before / after の UI 実測比較 |
| Track C | 第1段完了 | `tension` / `unresolved_tensions` の減衰を強化し、`active_themes` を append-only から再ランキング方式へ変更した | UI での定性再確認と必要なら係数再調整 |

### Track A: Response-Length Control

#### 目的

`short / medium / long` を設計意図として機能させる。

#### 変更内容

1. `PersonaSupervisorNode` の prompt に、length の選択基準を明示する
2. `SurfaceRealizationNode` の prompt に、length ごとの文数目安を入れる
3. `UtterancePlannerNode` で、length に応じて
   - opening style
   - avoid 条件
   - follow-up 許容量
   を変える
4. explanation / repair / boundary 系のシナリオテストを追加する

#### 完了条件

- `medium` 指定時に 2-4 文程度の返答が安定して出る
- `long` 指定時に一行返答へ潰れない
- `short` の切れ味は維持される

#### 実行状況

- 完了
- `PersonaSupervisorNode` prompt に length の選択基準を追加した
- `SurfaceRealizationNode` prompt に `short: 1-2文 / medium: 2-4文 / long: 4-6文` の目安を追加した
- `UtterancePlannerNode` の blueprint 生成を length-aware にした
- 関連の unit test を追加し、短文偏重に戻らないことを固定した

### Track B: Latency Reduction

#### 目的

対話 UI の 1 ターンあたり待機時間を短縮する。

#### 変更内容

1. Streamlit 側で graph / llm の再構築を避ける
   - session state か resource cache に保持する
2. 各ノードに timing trace を入れる
   - `internal_dynamics_ms`
   - `persona_supervisor_ms`
   - `surface_realization_ms`
   - `memory_commit_ms`
3. 3-pass 構成のボトルネックを可視化する
4. `PersonaSupervisorNode + SurfaceRealizationNode` の統合案を feature flag で試す

#### 統合案の意図

最初に潰す候補は `internal_dynamics` ではなく、
`persona_supervisor` と `surface_realization` である。

理由:

- `internal_dynamics` は event flag と dominant desire の source なので分離価値が高い
- `persona_supervisor` と `surface_realization` はどちらも表出設計レイヤーで、結合しやすい
- ここを 2 pass に圧縮できれば、体感改善が最も大きい

#### 完了条件

- UI 実測で平均ターン時間が改善する
- 既存人格性を大きく壊さない
- 2-pass runtime を安定して維持できる

#### 実行状況

- 完了
- Streamlit 側で compiled graph / llm の再構築を避ける runtime cache を導入した
- 主要ノードに timing trace を追加した
- Chat の trace UI と Dashboard に timing 可視化を追加した
- `PersonaSupervisorNode` が frame と final response をまとめて返す 2-pass runtime を標準化した
- spot check では combined path 実行時に `trace.supervisor` と `trace.surface_realization` を保持したまま `utterance_planner` を通らないことを確認した

### Track C: Tension Decay Rebalance

#### 目的

高圧ターンの余熱は残しつつ、修復や言い直しで前景から下がるようにする。

#### 変更内容

1. relationship delta を再調整する
   - `reassurance_received`
   - `repair_attempt`
   - `affectionate_exchange`
2. `unresolved_tensions` に条件付き強減衰を導入する
   - reassurance + repair の連続発火時は追加減衰
   - dominant desire が別テーマへ移った場合は自然減衰
3. unresolved theme と top-level `relationship.tension` を少し切り分ける
   - 生理的余熱
   - 物語的未解決テーマ
4. `working_memory.active_themes` に freshness / eviction を入れる
   - 最新優先
   - 一定ターン未強化なら後退
   - repair 後は前景から外れやすくする

#### 設計上の注意

- tension を即ゼロにはしない
- persona の執着や residue は残す
- ただし、冗談や修復後も同じテーマが過剰に居座る状態は避ける

#### 完了条件

- `repair_attempt` 後に `Top tension` が高止まりしにくくなる
- Dashboard 上でテーマ遷移が自然になる
- `active_themes` が固定化しにくくなる

#### 実行状況

- 第1段完了
- relationship rule の減衰側を強めた
  - `reassurance_received`: `tension -0.05`
  - `repair_attempt`: `tension -0.06`
- `relationship.tension` に自然減衰を導入し、緊張上昇イベントがないターンでは少しずつ下がるようにした
- `unresolved_tensions` は毎ターン passive decay し、repair / reassurance 時は追加減衰するようにした
- `working_memory.active_themes` は append-only をやめ、既存 theme / unresolved tension / dominant desire / emotional memory candidate を再スコアして前景テーマを再構成する方式に変えた
- state update / node / golden scenario のテストを更新した

## 5. 検証計画

### 5.1 自動テスト

- unit:
  - state update delta
  - unresolved tension decay
  - working memory eviction
  - prompt structure
  - planner の length-aware candidate 生成
- integration:
  - 旧 3-pass
  - 新 2-pass feature flag

### 5.2 定性シナリオ

最低限、以下を再実行する。

1. 初回の自己定位
2. 比較刺激
3. 修復
4. 独占要求
5. 理由説明を求めるターン

### 5.3 観測指標

- turn latency
- LLM call 数
- selected mode の変化
- `relationship.tension`
- `unresolved_tensions`
- `working_memory.active_themes`
- 返答文字数 / 文数

## 6. 実装順

1. Response-Length Control を先に固定する
   - 完了
2. Streamlit 側の再構築を止め、timing trace を入れる
   - 完了
3. tension / active theme の decay を再設計する
   - 第1段完了
4. 2-pass 統合を feature flag で試す
   - 完了
5. UI で再度 qualitative QA を回す
   - 未着手

## 7. 非目標

この Phase では次は扱わない。

- モデル変更そのもの
- retrieval 基盤の全面刷新
- persona schema の大改造
- 新しい評価カテゴリの追加

## 8. 成功条件

この Phase が成功といえる条件は次の通り。

1. 返答が状況に応じて短すぎず長すぎない
2. 修復後に緊張テーマが前景から下がる
3. 体感待機時間が改善する
4. `cold_attached_idol` の人格らしさが維持される

## 9. 現在の評価

2026-03-17 時点では、Phase 7 は「実装完了、定性再評価待ち」の段階にある。

- Response-Length Control: 実装済み
- Latency Reduction: 実装済み
- Tension Decay Rebalance: 第1段の係数調整と theme eviction を実装済み
- 未了: UI 上での before / after 比較と、必要なら decay 係数の再調整
