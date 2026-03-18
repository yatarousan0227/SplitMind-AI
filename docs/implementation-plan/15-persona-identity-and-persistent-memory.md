# 15. Persona Identity And Persistent Memory

## 目的

次の 2 点を、現行 runtime に自然に接続できる最小構成で実装する。

- persona が自分自身の名前として認識する `identity.self_name`
- セッションをまたいで関係性と心理的連続性を引き継ぐ persistent memory

このフェーズでは Obsidian/Vault には戻らず、frontmatter 付き Markdown card store を source of truth にする。

## 方針

- 記憶スコープは `user_id x persona_name`
- transcript 全保存はしない
- 保存単位は `relationship card + psychological card + episodes + session digests`
- bootstrap では全件ロードせず、必要最小限の card と episode だけを読む
- `self_name` は固定の自己認識名であり、保存キーには使わない

## 保存レイアウト

```text
data/memory/
  <user_id>/
    <persona_name>/
      relationship-card.md
      psychological-card.md
      episodes/
        <timestamp>-<slug>.md
      sessions/
        <session_id>.md
```

各ファイルは frontmatter を持ち、本文は人間が点検できる短い summary に限定する。

## 実装要点

- `PersonaProfile` に `identity` を追加し、`self_name` を必須化する
- prompt builder の `Persona Identity` に `gender`, `self_name`, `display_name` を渡す
- `MarkdownMemoryStore` を導入し、bootstrap / turn commit / session commit を集約する
- `SessionBootstrapNode` は relationship card, psychological card, episodes, session digests を読む
- `MemoryCommitNode` は turn 終了時に relationship / psychological / episode を更新する
- `run_session()` は終了時に session digest を `sessions/<session_id>.md` へ保存する

## コンテキスト制御

- bootstrap 注入は `relationship-card` 1 件、`psychological-card` 1 件、`episodes` 最大 4 件
- `working_memory` には raw history を持たせず、選択済み episode の ID と要約だけを持つ
- `episodes` は件数上限を設け、古く低 salience なものは compaction する

## 初期スコープ外

- 旧 Vault データの移行
- embeddings / vector search
- `self_name` の関係進行による動的変化
- transcript の完全保存
