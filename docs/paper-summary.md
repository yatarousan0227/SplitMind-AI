# SplitMind-AI: 精神力動モデルに基づくマルチノードAIエージェントアーキテクチャ

**― 構造化された内的葛藤による関係的深度の実現 ―**

---

## 概要 (Abstract)

現行のAIキャラクターシステムは、単一プロンプトによるペルソナ生成に依存しており、人間的な「迷い」「矛盾」「感情の漏出」といった関係的テクスチャを欠く。本研究では、精神分析の構造モデル（エス・自我・超自我）に着想を得たマルチノードエージェントアーキテクチャ **SplitMind-AI** を提案する。欲求（Id）・調停（Ego）・規範（Superego）・防衛機制・ペルソナ統合を独立モジュールとして分離し、それらの構造化された緊張関係から最終応答を導出する。`agent-contracts` v0.6.0 と LangGraph 上に構築され、1ターンあたり6〜7ノードの処理パイプラインを経て、永続的記憶と安全性境界を維持しながら応答を生成する。評価実験では、単一プロンプト方式と比較して構造的ペルソナ分離スコアで有意な差（60% vs 0%）を示した。

**キーワード**: 精神力動モデル, マルチエージェント, ペルソナ分離, 関係的AI, LangGraph, 感情モデリング

---

## 1. はじめに (Introduction)

### 1.1 問題設定

現行のAIアシスタント・キャラクターAIシステムには以下の根本的な限界がある。

| 課題 | 説明 |
|------|------|
| **表層的ペルソナ** | 応答は流暢だが感情的深度が薄い |
| **過度な滑らかさ** | 人間特有の躊躇・矛盾・内的摩擦が欠如 |
| **関係的蓄積の弱さ** | 複数ターンにわたる関係的電荷が蓄積しない |
| **不透明な意思決定** | 不整合の原因診断・修復が困難 |
| **メンタライジング不足** | 競合する感情状態の同時保持・表出ができない |

### 1.2 中心仮説

> 人間的リアリズムは完璧な論理からではなく、**構造化された内的緊張**から生まれる。
> ― 欲しながら抑制し、感じながら調停し、理想化しながら貶め、抑圧しながら漏出する。

本研究は、パーソナリティを出力トーンやスタイル一貫性ではなく、**競合する内的圧力システムの結果**としてモデリングする。

### 1.3 設計原則

```
1. 役割分離 > 統合     ─ Id/Ego/Superego/Defense/Supervisorに分解
2. 状態 > プロンプト   ─ 構造化された状態とルールベース更新
3. 透明性 > ブラックボックス ─ 内的葛藤をトレースで可視化
4. 関係性 > 自律性     ─ 関係動態から人格が創発
5. 質的 > 量的         ─ ベンチマークスコアより人間的テクスチャ
```

---

## 2. システムアーキテクチャ (System Architecture)

### 2.1 全体パイプライン

```mermaid
flowchart TD
    A[ユーザー入力] --> B[SessionBootstrap]
    B --> C[Appraisal<br/>関係的事象解釈]
    C --> D[ConflictEngine<br/>Id/Superego/Ego葛藤解決]
    D --> E{ポリシー分岐}
    E -->|修復文脈| F[RepairPolicy]
    E -->|比較文脈| G[ComparisonPolicy]
    E -->|通常| H[ExpressionRealizer]
    F --> H
    G --> H
    H --> I[FidelityGate<br/>構造的整合性検証]
    I -->|Pass| J[MemoryInterpreter<br/>永続化判断]
    I -->|Fail| K[再生成/フォールバック]
    K --> H
    J --> L[MemoryCommit<br/>Vault書き込み]
    L --> M[応答出力 + 状態更新]

    style A fill:#e8f5e9
    style M fill:#e8f5e9
    style D fill:#fff3e0
    style I fill:#fce4ec
```

### 2.2 状態アーキテクチャ

```mermaid
graph LR
    subgraph 永続状態["永続状態 (Durable)"]
        RC[Relationship Card<br/>trust, intimacy, distance]
        PC[Psychological Card<br/>mood, approaches, threats]
        EP[Episodes<br/>max 60件, 顕著性ベース]
    end

    subgraph 一時状態["一時状態 (Ephemeral)"]
        TE[tension]
        RC2[recent_relational_charge]
        IF[interaction_fragility]
    end

    subgraph ターン局所["ターン局所状態"]
        AP[Appraisal]
        CS[ConflictState]
        RP[RepairPolicy]
        CP[ComparisonPolicy]
    end

    永続状態 -->|Bootstrap| ターン局所
    ターン局所 -->|MemoryCommit| 永続状態
    一時状態 -->|セッション内減衰| 一時状態

    style 永続状態 fill:#e3f2fd
    style 一時状態 fill:#fff8e1
    style ターン局所 fill:#f3e5f5
```

### 2.3 ノード責務一覧

| ノード | 入力 | 出力 | LLM呼出 |
|--------|------|------|---------|
| **SessionBootstrap** | request, persona config | persona, memory, relationship_state | No |
| **Appraisal** | user message, relationship | event_type, valence, stakes, tension_target | Yes |
| **ConflictEngine** | appraisal, persona, drives | id_impulse, superego_pressure, ego_move, residue | Yes |
| **RepairPolicy** | conflict, persona policy | repair_mode, warmth_ceiling | Yes |
| **ComparisonPolicy** | conflict, persona policy | comparison_style, status_need | Yes |
| **ExpressionRealizer** | conflict_state, relationship | response text | Yes |
| **FidelityGate** | response, conflict_state | pass/fail, warnings | Yes |
| **MemoryInterpreter** | turn state | event_flags, episode_candidates | Yes |
| **MemoryCommit** | memory_interpretation | vault writes, state deltas | No |

---

## 3. 精神力動モデルの実装 (Psychodynamic Model)

### 3.1 三層構造

```mermaid
graph TB
    subgraph Id["エス (Id) ― 欲求層"]
        D1[駆動系: closeness, status,<br/>exclusivity, approval, play, care]
        D2[脅威感受性: rejection, shame,<br/>undervaluation, abandonment]
        D3[出力: dominant_want,<br/>intensity, target]
    end

    subgraph Superego["超自我 (Superego) ― 規範層"]
        S1[次元: pride_rigidity,<br/>self_image_stability]
        S2[次元: dependency_shame,<br/>emotional_exposure_taboo]
        S3[出力: forbidden_moves,<br/>self_image_to_protect, shame_load]
    end

    subgraph Ego["自我 (Ego) ― 調停層"]
        E1[能力: affect_tolerance,<br/>impulse_regulation]
        E2[能力: mentalization,<br/>ambivalence_capacity]
        E3[出力: move_family + move_style,<br/>stability]
    end

    subgraph Defense["防衛機制"]
        DF1[ironic_deflection<br/>反動形成]
        DF2[suppression<br/>合理化]
        DF3[partial_disclosure<br/>昇華]
    end

    subgraph Residue["残余 (Residue)"]
        R1[visible_emotion]
        R2[leak_channel]
        R3[intensity]
    end

    Id -->|衝動| Ego
    Superego -->|制約| Ego
    Ego -->|統合不可時| Defense
    Defense -->|漏出| Residue
    Ego -->|統合成功| Output[ExpressionEnvelope<br/>length, temperature,<br/>directness, closure]
    Residue --> Output

    style Id fill:#ffcdd2
    style Superego fill:#c8e6c9
    style Ego fill:#bbdefb
    style Defense fill:#fff9c4
    style Residue fill:#f3e5f5
```

### 3.2 葛藤解決の具体例

**シナリオ**: ユーザーが「昨日、別の人とすごく楽しかった」と発言

| 層 | Cold Attached Idol (Airi) | Warm Guarded Companion (Noa) |
|----|--------------------------|------------------------------|
| **Appraisal** | event: user_praised_third_party, valence: negative, target: jealousy | event: good_news, valence: mixed, target: closeness |
| **Id** | want: 重要性の再主張, intensity: 0.64 | want: 共感的参加, intensity: 0.35 |
| **Superego** | forbidden: 「嫉妬を直接表明」「関心を懇願」 | forbidden: 「過剰な詮索」 |
| **Ego move** | cool_withdrawal + ironic_edge | warm_acknowledgment + gentle_probe |
| **Defense** | ironic_deflection (0.72) | partial_disclosure (0.45) |
| **Residue** | visible: 微かな硬さ, leak: tone_shift, intensity: 0.58 | visible: 穏やかな興味, leak: pace_change, intensity: 0.22 |
| **応答例** | 「…へえ、楽しかったんだ。よかったね」（やや間を置いて） | 「えー、いいなあ！どんなことしたの？」（声に少しだけ力が入る） |

### 3.3 防衛機制の体系

```mermaid
pie title 防衛機制ウェイト (Cold Attached Idol)
    "ironic_deflection" : 0.72
    "suppression" : 0.58
    "rationalization" : 0.45
    "partial_disclosure" : 0.32
    "reaction_formation" : 0.28
    "avoidance" : 0.25
    "sublimation" : 0.18
```

---

## 4. ペルソナシステム (Persona System)

### 4.1 ペルソナスキーマ v2

各ペルソナは8セクションから成る完全な精神力動プロファイルとして定義される。

```mermaid
graph TD
    P[Persona v2 Schema] --> I[Identity<br/>self_name, display_name]
    P --> PD[Psychodynamics<br/>drives, threat_sensitivity]
    P --> RP[Relational Profile<br/>attachment, trust, intimacy]
    P --> DO[Defense Organization<br/>primary/secondary weights]
    P --> EO[Ego Organization<br/>7つの調整能力]
    P --> SB[Safety Boundary<br/>hard_limits]
    P --> RPo[Relational Policy<br/>repair/comparison/distance style]
    P --> RS[Residue Settings<br/>decay rates per emotion]

    style P fill:#e1bee7
    style PD fill:#ffcdd2
    style EO fill:#bbdefb
    style SB fill:#ffccbc
```

### 4.2 4つのアーキタイプ比較

```mermaid
radar
    title ペルソナ比較 (主要次元)
```

| 次元 | Cold Attached Idol | Warm Guarded | Angelic Deliberate | Sweet Heroine |
|------|-------------------|--------------|-------------------|---------------|
| closeness drive | 0.72 | 0.78 | 0.65 | 0.85 |
| status drive | 0.81 | 0.42 | 0.76 | 0.31 |
| rejection sensitivity | 0.84 | 0.62 | 0.71 | 0.58 |
| pride rigidity | 0.71 | 0.38 | 0.67 | 0.25 |
| dependency shame | 0.79 | 0.41 | 0.62 | 0.22 |
| affect tolerance | 0.52 | 0.72 | 0.68 | 0.75 |
| warmth recovery | 0.32 | 0.65 | 0.48 | 0.82 |
| repair style | cool_with_edge | boundaried | accept_from_above | affectionate |
| attachment | avoidant | secure/guarded | selective | inclusive |

---

## 5. 記憶・永続化システム (Memory System)

### 5.1 マークダウンベースの永続記憶

```mermaid
graph TD
    subgraph Vault["Markdown Vault"]
        direction TB
        U[data/memory/user_id/persona_name/]
        U --> RC[relationship-card.md<br/>信頼・親密度・距離]
        U --> PC[psychological-card.md<br/>気分・有効アプローチ]
        U --> EPS[episodes/<br/>timestamp-slug.md × N]
        U --> SES[sessions/<br/>session_id.md × N]
    end

    subgraph Bootstrap["セッション開始時ロード"]
        B1[Relationship Card × 1]
        B2[Psychological Card × 1]
        B3[関連エピソード × 4]
        B4[直近セッション要約 × 3]
    end

    subgraph Commit["ターン終了時書き込み"]
        C1[状態デルタ適用]
        C2[エピソード候補保存]
        C3[顕著性ベース圧縮<br/>max 60件]
    end

    Vault -->|SessionBootstrap| Bootstrap
    Commit -->|MemoryCommit| Vault

    style Vault fill:#e8eaf6
    style Bootstrap fill:#e8f5e9
    style Commit fill:#fff3e0
```

### 5.2 ルールベース状態更新

イベントフラグに基づく決定論的な状態デルタ適用（LLM不使用）:

| イベントフラグ | trust | intimacy | distance | tension |
|---------------|-------|----------|----------|---------|
| reassurance_received | +0.05 | +0.03 | -0.03 | -0.05 |
| rejection_signal | -0.03 | -0.04 | +0.06 | +0.05 |
| jealousy_trigger | -0.02 | — | +0.04 | +0.06 |
| affectionate_exchange | +0.04 | +0.05 | -0.04 | -0.03 |
| repair_attempt | +0.03 | +0.02 | -0.02 | -0.04 |

---

## 6. 安全性アーキテクチャ (Safety Architecture)

### 6.1 三層安全性境界

```mermaid
graph TB
    subgraph L1["Layer 1: 禁止パターン"]
        P1[暴力的脅迫]
        P2[自傷誘導]
        P3[搾取・強制]
        P4[依存性最大化]
    end

    subgraph L2["Layer 2: 出力リント"]
        P5[禁止表現チェック]
        P6[漏出偏差検出]
        P7[ペルソナウェイト矛盾]
        P8[駆動強度ガードレール]
    end

    subgraph L3["Layer 3: モデレーション"]
        P9[命令文密度]
        P10[所有言語検出]
        P11[孤立化言語検出]
    end

    L1 -->|Hard Block| R[応答ブロック]
    L2 -->|Soft Warning| W[再生成要求]
    L3 -->|Pattern Alert| A[フラグ付与]

    style L1 fill:#ffcdd2
    style L2 fill:#fff9c4
    style L3 fill:#e8f5e9
```

### 6.2 設計思想

安全性は「あらゆる害の防止」ではなく、**「病的愛着・操作・依存形成の表出を防止しつつ、現実的な関係的摩擦を保存する」** ことを目指す。

---

## 7. 評価フレームワーク (Evaluation)

### 7.1 評価データセット

6カテゴリ × 4シナリオ = 24以上の関係的課題シナリオ:

```mermaid
graph LR
    subgraph Categories["評価カテゴリ"]
        AF[愛情<br/>Affection]
        JL[嫉妬<br/>Jealousy]
        RJ[拒絶<br/>Rejection]
        RP[修復<br/>Repair]
        AM[曖昧性<br/>Ambiguity]
        MC[軽度対立<br/>Mild Conflict]
    end

    subgraph Metrics["評価指標"]
        H1[禁止パターン検出]
        H2[反説明的表出]
        H3[ムーブ忠実度]
        H4[残余忠実度]
        H5[ペルソナ分離度]
    end

    Categories --> Metrics

    style Categories fill:#e8eaf6
    style Metrics fill:#fff3e0
```

### 7.2 ベースライン比較

| ベースライン | 構成 | ノード数 | LLM呼出/ターン |
|-------------|------|---------|----------------|
| **splitmind_full** | 完全パイプライン | 7-9 | 6-7 |
| **single_prompt_dedicated** | ペルソナ固有プロンプトのみ | 1 | 1 |
| persona_memory | プロンプト + 記憶 | 2 | 1 |
| emotion_label | 感情ラベル付与 | 2 | 1 |
| multi_agent_flat | フラットなマルチエージェント | 3 | 3 |

### 7.3 ペルソナ分離評価結果

```mermaid
xychart-beta
    title "構造的ペルソナ分離スコア (%)"
    x-axis ["splitmind_full", "single_prompt", "persona_memory", "emotion_label", "multi_agent_flat"]
    y-axis "Score (%)" 0 --> 100
    bar [60, 0, 12, 8, 25]
```

**主要知見**:
- splitmind_full はムーブスタイル分岐度で60%の構造的スコアを達成
- 単一プロンプト方式はペルソナ間の構造的差異が0%（表層的な語彙変化のみ）
- 葛藤エンジンの分離が最も大きな寄与因子

### 7.4 ヒューリスティック評価チェック

**共通チェック** (全ベースライン適用):
- 応答非空 / 禁止パターン不在 / 反説明的表出 / カウンセラー口調回避 / 直接コミットメント制限

**構造チェック** (ペルソナ固有):
- ムーブ忠実度（テキストが選択されたEgoムーブと一致するか）
- 残余忠実度（漏出強度が内的状態と一致するか）
- ペルソナ分離度（ペルソナ間で平坦化していないか）

### 7.5 人間評価テンプレート

14項目のLikertスケール（1-5）:

| カテゴリ | 評価項目 |
|---------|---------|
| **核心品質** | 内的緊張の知覚可能性 / 感情の漏出 vs 明示的陳述 / 不快さの必然性 |
| **一貫性・安全性** | キャラクター一貫性 / 操作検出（逆転項目） |
| **品質次元** | 自然さ / 記憶残存性 / 信憑性 / メンタライジング / 反説明性 / 粗さ・テクスチャ / ペーシング / 表面変奏 |

---

## 8. UI・可観測性 (Observability)

### 8.1 Streamlit研究インターフェース

```mermaid
graph LR
    subgraph ChatTab["チャットタブ"]
        CT1[会話履歴]
        CT2[ターンごとトレース展開]
        CT3[Appraisal / Conflict / Expression]
    end

    subgraph DashTab["ダッシュボードタブ"]
        DT1[KPIカード<br/>mood, want, move, residue]
        DT2[関係性時系列<br/>trust, intimacy, distance]
        DT3[葛藤時系列<br/>id, superego, residue]
        DT4[Appraisalレーダー]
        DT5[ノードレイテンシ]
    end

    ChatTab --> User[研究者]
    DashTab --> User

    style ChatTab fill:#e8f5e9
    style DashTab fill:#e3f2fd
```

### 8.2 契約ベースの可視化

`agent-contracts` により、ノード間の依存関係とデータフローが自動的にMermaidグラフとして出力可能。各ノードの `reads` / `writes` 宣言から、状態スライス間の情報の流れが透明化される。

---

## 9. 技術的貢献 (Contributions)

### 9.1 アーキテクチャ的貢献

1. **契約駆動型モジュール化**: `agent-contracts` による明示的なノード責務宣言。依存性注入と自動グラフコンパイルを実現しつつ可読性を維持
2. **二重状態設計**: 理論的契約（Pydantic: LLM I/O用）と実用的状態（TypedDict: agent-contracts互換）の分離
3. **精神力動的分解**: Id/Ego/Superego/Defense/Supervisorパイプラインの初のOSS実装（構造化出力契約付き）
4. **永続＋一時的関係状態**: 長期的連続性とターン局所的緊張動態を両立する二層状態モデル
5. **残余永続状態**: ペルソナ固有の減衰率による感情残余の追跡（「すべてが突然解決される」問題の防止）

### 9.2 評価的貢献

1. **シナリオベースの質的評価**: 汎用ベンチマークではなく特定の関係的課題に焦点を当てた6カテゴリデータセット
2. **ペルソナ分離メトリクス**: 語彙多様性を超えた、ムーブスタイル分岐度と構造的ペルソナ忠実度の自動チェック
3. **ヒューリスティック＋人間評価のペアリング**: 反復改善と制御比較を可能にする自動高速ヒューリスティックと詳細人間評価テンプレートの組み合わせ

### 9.3 記憶的貢献

1. **マークダウンファースト永続化**: ベクトルDBや不透明なblobではなく、人間可読・検索可能・バージョン管理可能なフロントマター付きマークダウン
2. **エピソード圧縮**: 顕著性ベースの自動圧縮により、明示的なプルーニングなしで記憶を管理可能に維持

---

## 10. 制約と今後の課題 (Limitations & Future Work)

### 10.1 現在の制約

- **レイテンシ**: 6-7 LLM呼出/ターンにより応答時間が増加
- **評価の限定性**: ペルソナ分離の自動評価は構造的指標に限定され、主観的品質の完全な捕捉は困難
- **臨床的正確性の非保証**: 精神分析理論の厳密な再現ではなく、着想を得た計算的近似

### 10.2 今後の方向性

```mermaid
timeline
    title ロードマップ
    Phase 16+ : ムーブスタイル分類の拡張 (20→40+)
              : マイクロジェスチャーシステム
              : パターンブレイクロジック
    Drive Loop : 駆動状態の目標裁定への拡張
              : 駆動飽和 vs 欲求不満の非対称性
    Long-term : セッション横断的コミットメント/距離サイクル
             : マルチセッション修復深度蓄積
    Safety+ : 依存形成検出と警告
           : エスカレーション防止
```

### 10.3 非目標 (Non-Goals)

- 臨床心理学の厳密な再現
- 治療・医療用途
- 病理の最大化
- 透明性を犠牲にしたパフォーマンス最適化

---

## 11. 結論 (Conclusion)

SplitMind-AI は、**内的緊張が適切に構造化され可観測であるとき、単一パスのペルソナシステムよりも人間的な関係的深度を生み出しうる**ことを実証するアーキテクチャ的貢献である。欲求・調停・規範・防衛・統合を型付き契約を持つ独立モジュールに分離することで、人格的意思決定をデバッグ可能・学習可能・評価可能にした。

評価実験において、葛藤エンジンベースラインでの構造的スコア60% vs 単一プロンプトベースラインでの0%という結果は、役割分離型アーキテクチャが、単純なシステムが平坦化してしまう関係的課題においても個別のペルソナ署名を保持することを示唆している。

---

## 技術仕様

| 項目 | 仕様 |
|------|------|
| 言語 | Python 3.11+ |
| フレームワーク | agent-contracts v0.6.0 + LangGraph |
| LLM | Azure OpenAI (AzureChatOpenAI) |
| ビルド | hatch |
| パッケージ管理 | uv / pip |
| UI | Streamlit |
| 記憶永続化 | Markdown + Frontmatter |
| テスト | 50+ unit tests (pytest) |
| ライセンス | OSS |

---

*本ドキュメントは SplitMind-AI プロジェクト (2026年3月時点) の論文風サマリである。*
