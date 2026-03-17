# SplitMind-AI Implementation Plan

## 1. 目的

[`docs/concept.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/concept.md) を、実際に着手できる実装単位へ分解した計画書である。

今回の計画では、概念上の 5 役割

* Id
* Ego
* Superego
* Defense Mechanism
* Persona Supervisor

をそのまま 5 個の独立 LLM ノードに分けるのではなく、`docs/concept.md` の 20 章で定義された MVP 方針を優先する。

つまり MVP では以下を採用する。

1. 1ターンあたり LLM call は 2 回
2. Id / Ego / Superego / Defense は構造化推論
3. Persona Supervisor が最終文面を単一生成
4. 状態更新は Python 側のルールベース

そのうえで、`agent-contracts` の contract 駆動設計を利用し、役割境界・状態依存・トレースを明示する。

## 2. agent-contracts 前提

`agent-contracts` は `NodeContract` でノードの reads / writes / trigger conditions を宣言し、registry から LangGraph を自動構築するライブラリである。今回の計画では特に次を前提とする。

* `NodeContract` によるノード責務の明示
* `TriggerCondition` による rule-first routing
* Pydantic ベースの typed state
* registry + graph builder による自動配線
* CLI による validate / visualize / diff

参照:

* [agent-contracts GitHub](https://github.com/yatarousan0227/agent-contracts)
* [agent-contracts PyPI](https://pypi.org/project/agent-contracts/)
* [agent-contracts Docs](https://yatarousan0227.github.io/agent-contracts/)

## 3. 実装方針の要点

### 3.1 MVP のランタイム分解

概念上は 5 contract を保持するが、実行ノードはまず以下の 3 ノードに絞る。

1. `InternalDynamicsNode`
2. `PersonaSupervisorNode`
3. `MemoryCommitNode`

補助として `SessionBootstrapNode` と `ErrorNode` を追加する。

### 3.2 なぜ 5 ノード構成にしないか

`docs/concept.md` は 10 章で役割別 contract を定義している一方、20 章では「MVP は 2-call 構成」と明記している。初期段階で 5 役割を別々に LLM 実行すると、以下の問題が強い。

* call 数が増えて遅い
* 表出の声が割れる
* 比較実験より先に orchestration の複雑さを抱える
* `agent-contracts` の利点が「設計の明示」より「ノード数の多さ」に埋もれる

したがって MVP では、

* logical contracts は schema と trace として保持する
* runtime nodes は最小構成に圧縮する

という方針を取る。

### 3.3 保存戦略

保存先は 2 層に分ける。

* Python 側構造化状態: 現セッションの source of truth として扱う即時状態
* Obsidian Vault: セッションをまたいで再利用する長期記憶と関係履歴の source of truth

MVP では、1 セッション中は Python 側 state だけを更新し、各ターン終了時に Obsidian へスナップショットと記憶候補を書き出す。
次セッション開始時は、直近コミット済みの Obsidian 内容から Python 側 state を復元する。

## 4. フェーズ構成

### Phase 1

設計基盤と contract モデルを作る。

詳細: [`01-foundation-and-contract-model.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/01-foundation-and-contract-model.md)

### Phase 2

1ターン実行系、記憶更新、研究 UI を作る。

詳細: [`02-runtime-memory-and-ui.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/02-runtime-memory-and-ui.md)

### Phase 3

評価・安全境界・運用性を整える。

詳細: [`03-evaluation-and-hardening.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/03-evaluation-and-hardening.md)

### Phase 4

Vault 保存戦略を再設計し、セッション跨ぎの記憶連続性を実現する。

焦点:
- セッション要約の生成と保存（現状: 未実装）
- ムード状態の永続化（現状: 毎セッションリセット）
- 感情記憶スキーマの品質改善（emotion/trigger の分離、内容量拡充）
- セマンティック嗜好の生成ロジック実装（現状: 常に空）

詳細: [`04-vault-memory-redesign.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/04-vault-memory-redesign.md)

### Phase 5

間接表現と自然さを改善し、感情語の直接説明に寄りすぎる問題を抑える。

焦点:
- 間接表現タクソノミーの導入
- few-shot による自然表現の補強
- directness に応じた expression lint
- 感情名の直接使用に対する防護網

詳細: [`05-indirect-expression-naturalness.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/05-indirect-expression-naturalness.md)

### Phase 6

小手先の自然化ではなく、心理学と AI Agent を同じ制御ループへ載せるための再設計を行う。

焦点:
- appraisal state の導入
- social action arbitration の明示化
- memory の active retrieval 化
- utterance generation の candidate selection 化
- believability / mentalizing を含む評価軸の追加

詳細: [`06-psychology-agent-fusion-roadmap.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/06-psychology-agent-fusion-roadmap.md)

実装チェックリスト: [`06-implementation-tasklist.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/06-implementation-tasklist.md)

### Phase 7

体感速度、tension の残留、応答長の短文偏重を改善する。

焦点:
- 返答長の状況適応
- UI / ノード単位のレイテンシ改善
- tension / unresolved theme の減衰再設計
- working memory theme の eviction

進捗:
- Track A: 実装済み
- Track B: 実装済み
- Track C: 第1段完了
- 残りは UI 上での before / after 定性確認

詳細: [`07-performance-tension-and-response-length.md`](/Users/iwasakishinya/Documents/hook/SplitMind-AI/docs/implementation-plan/07-performance-tension-and-response-length.md)

### Phase 8

仕様上は存在する「欲求・衝動・本能」を、単一ラベルではなく持続する drive state として扱い、
appraisal / action policy / memory をまたぐ駆動系へ引き上げる。

焦点:
- `dominant_desire` 一本足から `drive_state` への移行
- frustration / satiation / suppression / carryover の状態化
- drive competition に基づく行動選択
- target / wound / blocked action ベースの記憶再活性化
- Streamlit 研究 UI の `drive_state` 前提への再設計
- 欲求強化と安全境界の両立

進捗:
- Track A: 実装済み
- Track B: 実装済み
- Track C: 実装済み
- Track D: 実装済み
- Track E: 実装済み
- Track F: 実装済み
- 残りは eval の継続観測と `dominant_desire` 参照の後始末

詳細: [`08-drive-and-instinct-loop.md`](08-drive-and-instinct-loop.md)

## 5. 推奨ディレクトリ構成

初期実装では以下を推奨する。

```text
SplitMind-AI/
├── docs/
│   ├── concept.md
│   └── implementation-plan/
├── src/
│   └── splitmind_ai/
│       ├── app/
│       ├── contracts/
│       ├── nodes/
│       ├── prompts/
│       ├── state/
│       ├── memory/
│       ├── personas/
│       ├── rules/
│       ├── ui/
│       └── eval/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── golden/
├── configs/
│   ├── agent_config.yaml
│   ├── personas/
│   └── prompts/
└── vault/
```

## 6. 最初のマイルストーン定義

最初の実装完了ラインは次とする。

1. 単一ペルソナで 1ターン実行できる
2. internal dynamics trace を JSON で残せる
3. relationship state / mood state をルール更新できる
4. Obsidian に session summary と emotional memory を保存できる
5. 研究 UI 上で final response と主要 trace を確認できる

## 7. 非採用事項

初期段階では以下を見送る。

* 5 役割すべての独立 LLM ノード化
* ベクトル DB 前提の複雑な記憶検索
* 本番向け認証やマルチユーザー基盤
* 音声や画像を含むマルチモーダル化
* 自動チューニングや fine-tuning
