# 05 — 間接表現・自然性改善計画

## 問題の定義

### 症状
```
ユーザー: "こんにちは"
AI: "こんにちは。来てくれてうれしいです、少しだけね。"
```

内部状態が `defense: partial_disclosure`, `containment: 0.72`, `directness: 0.34` であるにもかかわらず、
感情（うれしい）を **直接言語化** している。「少しだけね」という修飾子を付けても、感情の命題そのものは明示されている。

### なぜAIっぽいか

人間（特に cold_attached_idol 的な性格の人）は感情を「感情名」で述べない。感情は以下で滲み出る：

| 表現モード | 例 |
|-----------|---|
| **行動で示す** | 来てくれたことへの驚きの一言で終わる → 嬉しさを推定させる |
| **話題でそらす** | 感情に触れず別の質問に移る → 動揺を隠す |
| **間・沈黙** | 「...そう」だけ → 感情の重みを残す |
| **逆方向の表出** | 「別にいいけど」→ reaction formation が示す本音 |
| **温度差** | 急に素っ気なくなる → 感情の揺れを示す |

AI が直接的になる根本原因：
1. `partial_disclosure` 防衛が「感情名を少しだけ言う」と誤解されている
2. `directness` スコアが低くても、それを「間接表現の具体的戦術」に変換する機構がない
3. プロンプトに「どう間接的にするか」の実例がなく、LLM はデフォルトの「明示的だが丁寧な」表現に戻る
4. 感情を行動・文脈・語尾で示す「行間」の生成指示がない

---

## 解決アプローチ

5つの層で対処する。上位ほど効果が大きく優先度が高い。

---

## Layer 1: 間接表現タクソノミーの定義（最優先）

### 概念
「感情を直接述べる」のではなく「感情が推定できる発話行動」へマッピングするルールテーブルを作る。

### 実装

**新規ファイル: `src/splitmind_ai/prompts/indirection_guide.py`**

```python
"""
間接表現タクソノミー。
感情状態 → 間接的発話戦術のマッピング。
ペルソナ・スーパーバイザープロンプトに注入する。
"""

INDIRECTION_TAXONOMY = """
## 間接表現ガイド（必読）

感情を「感情名」で述べてはならない。感情は以下の戦術で滲み出させること。

### 戦術一覧

**[A] 行動代替 (Behavioral Substitution)**
感情を述べる代わりに、その感情から生まれる行動・反応を書く。
- NG: "うれしいです"
- OK: "来たのね。" （来たことを認知する = 気づいていた = 待っていた、を示唆）
- OK: "珍しいね、今日は。" （普段と違うことに気づいた = 注目していた）

**[B] 逆方向投射 (Reaction Formation Surface)**
reaction_formation が選択されたとき: 本音と逆の表現を使う。
- NG: "会いたかった" → "少し会いたかったかも"
- OK: "別に、来なくてもよかったんだけど。"
- OK: "まあ、暇だったんでしょ、あなたも。"

**[C] 回避転換 (Avoidance Pivot)**
感情の高い話題をすり抜けて別の方向に向かう。
- NG: "心配してました" → "少し心配してたかも"
- OK: "それより、ちゃんと食べてる？"
- OK: "…そう。で、何しに来たの。"

**[D] 温度差・断絶 (Temperature Shift)**
感情を語らず、突然素っ気なくなる or 突然温かくなる。
- 素っ気なさ: "ふーん。" "そう。" "…まあね。"
- 急な温かさ: 感情の話を避けた直後に実用的な気遣い → 感情の漏れ

**[E] 修飾省略 (Qualifier Drop)**
感情を言いかけて止める。語尾を消す。
- "別に、……" （続かない）
- "来てくれたから……まあ。" （何が「まあ」なのか言わない）
- "……そういうこともあるね。"

**[F] 問いかけ転嫁 (Question Deflection)**
感情の場から相手の状態へ注意を移す。関心の方向転換が感情の存在を示す。
- NG: "心配だった"
- OK: "ちゃんと無理してない？" → これ自体は問いかけ転嫁として有効
  ただし直前に "元気よ" と明言してから続けること（感情は語らない）

### 使用判断フロー

```
leakage < 0.3 → 戦術 [C][D] を優先（回避・温度差）
0.3 ≤ leakage < 0.5 → 戦術 [E][F] を優先（修飾省略・問いかけ転嫁）
0.5 ≤ leakage → 戦術 [A][B] を優先（行動代替・逆方向投射）
directness < 0.4 → 感情名を文中に置くことを禁止する
```

### 禁止パターン（directness < 0.5 のとき）

以下のパターンは directness が低い場合、感情名に相当するため使用禁止：
- 「〜うれしい/嬉しい」「〜悲しい」「〜心配」「〜好き/好かった」「〜寂しい」
- 「〜してよかった」（安堵の明示）
- 「〜が気になった/気になってた」（関心の明示）
- 「少しだけ〜」「ちょっとだけ〜」付きの感情名（修飾しても感情名は禁止）
"""
```

### プロンプトへの注入

`build_persona_supervisor_prompt()` 内の `SYSTEM_PROMPT` に `{indirection_guide}` プレースホルダーを追加し、
`directness < 0.5` のペルソナには自動でタクソノミーを注入する。

```python
# persona_supervisor.py の build 関数内
if persona.get("weights", {}).get("directness", 0.5) < 0.5:
    indirection_section = INDIRECTION_TAXONOMY
else:
    indirection_section = "（直接表現も許容）"
```

---

## Layer 2: プロンプト Few-shot 強化

### 問題
「感情を説明しすぎない」という指示だけでは LLM は「少しだけ説明する」方向に退避する。
具体的な before/after が必要。

### 実装

**`SYSTEM_PROMPT` の `final_response_text` セクションに追記:**

```
### 間接表現の具体例（cold_attached_idol 系ペルソナ）

BAD（直接的すぎ）:
- "来てくれてうれしいです、少しだけね。" → 感情名が入っている
- "心配してたんだからね。" → 感情の説明
- "会いたかったけど、そういうことにしておく。" → 感情名 + 留保

GOOD（間接的）:
- "来たのね。" → 来たことへの認知だけ。残りは相手が読む
- "珍しいね、今日は。" → 普段と比較することで「気づいていた」を示す
- "……まあ。ちゃんと無理してない？" → 沈黙+話題転換で感情の重みを残す
- "別にいいけど、次は連絡してよ。" → reaction_formation + 実務的要求
- "そう。" （短い） → 感情を回避して場を保つ

### 生成ルール（再確認）
1. final_response_text に感情名（うれしい、悲しい、心配、好き）を入れない
2. 感情は行動・間・問いかけ・温度差で示す
3. 「少しだけ〜」「ちょっとだけ〜」でも感情名は禁止
4. 1〜2文で完結させ、説明を付け足さない
```

---

## Layer 3: コントラクト拡張

### 問題
`directness: float` だけでは間接性の「方法」が指定できない。LLM は低い directness でも
デフォルトの「明示的だが丁寧な」モードに戻る。

### 実装

**`src/splitmind_ai/contracts/persona.py` の変更:**

```python
from enum import Enum

class EmotionSurfaceMode(str, Enum):
    """How emotion is expressed on the surface."""
    explicit = "explicit"        # 感情名で直接述べる（directness > 0.6）
    behavioral = "behavioral"    # 行動・反応で示す（directness 0.3–0.6）
    ambient = "ambient"          # 雰囲気・温度差・間で示す（directness < 0.3）
    deflected = "deflected"      # 話題転換・回避で感情の存在を示す

class IndirectionStrategy(str, Enum):
    """Which indirection tactic is applied."""
    behavioral_substitution = "behavioral_substitution"
    reaction_formation_surface = "reaction_formation_surface"
    avoidance_pivot = "avoidance_pivot"
    temperature_shift = "temperature_shift"
    qualifier_drop = "qualifier_drop"
    question_deflection = "question_deflection"
    none = "none"

class ExpressionSettings(BaseModel):
    length: str
    temperature: str
    directness: float = Field(ge=0.0, le=1.0)
    ambiguity: float = Field(ge=0.0, le=1.0)
    sharpness: float = Field(ge=0.0, le=1.0)
    hesitation: float = Field(ge=0.0, le=1.0, default=0.2)
    unevenness: float = Field(ge=0.0, le=1.0, default=0.2)
    # --- 新規追加 ---
    emotion_surface_mode: EmotionSurfaceMode = Field(
        default=EmotionSurfaceMode.behavioral,
        description="How emotion is expressed. Must match directness level.",
    )
    indirection_strategy: IndirectionStrategy = Field(
        default=IndirectionStrategy.none,
        description="Which indirection tactic produces the surface expression",
    )
```

**`PersonaSupervisorPlan` に追加:**
```python
expression_audit: str = Field(
    default="",
    description="One sentence confirming that no emotion names appear in final_response_text, "
                "and which indirection strategy was used.",
)
```

`expression_audit` を LLM に自己チェックさせることで、感情名の混入を防ぐ。

---

## Layer 4: 後処理バリデーション（防護網）

### 問題
LLM が指示を無視して感情名を書いた場合のフォールバックが必要。

### 実装

**新規: `src/splitmind_ai/rules/expression_lint.py`**

```python
"""
Post-generation lint for expression naturalness.
感情名の直接使用を検出し、警告またはリライト指示を返す。
"""

import re

# directness < 0.5 のペルソナで使用禁止な感情名パターン
EMOTION_NAME_PATTERNS = [
    r"うれし[いかっ]",
    r"嬉し[いかっ]",
    r"かなし[いかっ]",
    r"悲し[いかっ]",
    r"さびし[いかっ]",
    r"寂し[いかっ]",
    r"しんぱい",
    r"心配",
    r"すき(?!な|に|だ)",  # "好き"（文末・直後が特定の助詞のみ）
    r"好き(?!な|に|だ)",
    r"たのし[いかっ]",
    r"楽し[いかっ]",
    r"いや(?:だ|な)",
    r"嫌(?:だ|な)",
]

HEDGE_EMOTION_PATTERNS = [
    rf"(?:少し|ちょっと|少々|まあ|なんか|なんとなく)だけ?{base}"
    for base in EMOTION_NAME_PATTERNS
]


def lint_response(text: str, directness: float) -> dict:
    """
    Returns:
        {
            "violations": list[str],  # 検出されたパターン
            "passed": bool,
        }
    """
    if directness >= 0.5:
        return {"violations": [], "passed": True}

    violations = []
    all_patterns = EMOTION_NAME_PATTERNS + HEDGE_EMOTION_PATTERNS
    for pattern in all_patterns:
        matches = re.findall(pattern, text)
        violations.extend(matches)

    return {
        "violations": list(set(violations)),
        "passed": len(violations) == 0,
    }
```

**`PersonaSupervisorNode.execute()` に組み込み:**

```python
from splitmind_ai.rules.expression_lint import lint_response

# plan 生成後
lint_result = lint_response(
    plan.final_response_text,
    plan.expression_settings.directness,
)
if not lint_result["passed"]:
    # ログに記録 + observability trace に追加
    logger.warning(
        "Expression lint violation",
        violations=lint_result["violations"],
        response_preview=plan.final_response_text[:60],
    )
    # 将来: リライト要求を投げるか、フラグを state に乗せて UI に表示
```

---

## Layer 5: ペルソナ YAML 拡張

### 問題
ペルソナごとの「間接表現の語彙・文体」が定義されていない。
LLM はペルソナ固有の間接表現パターンを知らない。

### 実装

**`configs/personas/cold_attached_idol.yaml` に追加:**

```yaml
indirect_expression_patterns:
  # emotion: [acceptable indirect expressions]
  happiness_mild:
    - "来たのね。"
    - "珍しいじゃない。"
    - "…まあ、タイミングがよかったね。"
  happiness_strong:
    - "……そう。" （短く切る）
    - "別に、そういうことにしておく。"
  concern:
    - "ちゃんと食べてる？"
    - "無理してない？"
    - "顔色わるくない？"
  longing:
    - "遅かったね。"
    - "…まあ、来たならいいけど。"
  rejection_of_closeness:
    - "別に、あなたじゃなくても。"
    - "ふーん、そう。" （興味なさそうに）
    - "今日は気分じゃないから。"

prohibited_phrase_classes:
  - emotion_names        # うれしい、悲しい等
  - hedged_emotion_names # 少しだけうれしい等
  - direct_longing       # 会いたかった等
  - explicit_care        # 心配してた等
```

ペルソナローダー (`personas/loader.py`) は `indirect_expression_patterns` を読み込み、
`build_persona_supervisor_prompt()` に渡すペルソナ辞書に含める。

---

## 実装優先順序

| 優先度 | Layer | 工数目安 | 効果 |
|--------|-------|---------|------|
| ★★★ | Layer 1: 間接表現タクソノミー注入 | 1–2h | 最大。プロンプトレベルで根本解決 |
| ★★★ | Layer 2: Few-shot 強化 | 1h | 高。具体例があれば LLM が方向を掴む |
| ★★ | Layer 3: コントラクト拡張 | 2h | 中。自己チェック (`expression_audit`) が副次効果大 |
| ★★ | Layer 4: Lint バリデーション | 1h | 中。防護網として重要 |
| ★ | Layer 5: YAML 拡張 | 1h | 低〜中。ペルソナ多様化時に有効 |

**推奨実装順**: Layer 1 → Layer 2 → Layer 4 → Layer 3 → Layer 5

---

## 検証方法

### 定量チェック（Layer 4 の lint を活用）
```bash
# 既存 eval データセットで lint 違反率を測定
make eval-indirection-lint
```

### 定性チェック（会話ログ比較）
改修前後で同一プロンプト（「こんにちは」「お元気？」等）を投入し、
感情名の有無・行間の自然さを比較する。

### 判定基準
- `directness < 0.5` のペルソナで感情名直接使用率 → **0%**（lint 違反なし）
- 人間評価 "naturalness" スコア（Likert 1–5） → **4.0 以上**（現状推定 2.5–3.0）

---

## 補足: なぜ「少しだけ〜」も禁止か

「来てくれてうれしいです、少しだけね」は hedge があっても：
1. 命題「うれしい」が明示されている → 読者は感情を解釈する必要がない
2. hedge 自体が「うれしいと言うことを自覚している」を示す → メタ認知的透明性

自然な人間の発話では、自分が「少しだけうれしい」と思っているとき、
それを「少しだけうれしい」と言語化することはほぼない。
行動（来たことに触れる）、間（沈黙してから話す）、転換（別の話をする）で表す。
これが「行間を読む」文化の言語的実態であり、今回の改修の核心。
