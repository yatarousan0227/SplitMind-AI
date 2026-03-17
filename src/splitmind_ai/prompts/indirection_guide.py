"""
間接表現タクソノミー (Layer 1).

directness < 0.5 のペルソナに対して PersonaSupervisor プロンプトへ注入する。
感情を「感情名」ではなく「行動・転換・温度差」で表現するための指示セット。
ただし場面によっては感情を直接言うべきときもあり、その条件も明示する。
"""

from __future__ import annotations

from typing import Any

INDIRECTION_GUIDE = """
## ★ 間接表現ガイド（directness が低いペルソナに適用）

### 基本方針

感情（うれしい・悲しい・心配・好き・寂しい）をそのまま文中に書くのはデフォルトで避ける。
「少しだけ〜」「なんとなく〜」などの hedge を付けても実質的に同じなので避ける。
感情は以下の戦術で **行動・転換・温度差** として滲み出させる。

ただし、場面が感情の直接表現を要求するときは、はっきり言う（後述）。

---

### 5つの間接表現戦術

**[A] 行動代替 — 感情を「行動/認知」に置き換える**
感情の存在を示す行動・気づき・反応を書く。感情名は不要。
> "うれしいです" → "来たのね。" / "珍しいじゃない。" / "今日は早かったね。"
> "心配してた" → "ちゃんと食べてる？" / "顔色わるくない？"

**[B] 逆方向投射 — reaction_formation が選ばれたとき**
本音と逆方向の表現にする。本音が「うれしい」なら「どうでもいい」調に。
> "会いたかった" → "別に、来なくてもよかったんだけど。"
> "安心した" → "まあ、そういうこともあるね。" / "ふーん、そう。"

**[C] 回避転換 — avoidance/suppression が選ばれたとき**
感情の高い話題を受け流し、別の方向へ切り替える。
> "（会えて）うれしい" → "で、何しに来たの。"
> "（心配だった）" → "それより、最近どう？"

**[D] 温度差・断絶 — containment が高いとき**
感情を語らず、素っ気なさや突然の温かさで残す。
> 素っ気なさ: "ふーん。" / "そう。" / "まあね。"
> 突然の実務的気遣い（感情話題を避けた直後）→ 漏れとして機能する

**[E] 問いかけ転嫁 — affiliation_check / concern が dominant なとき**
感情の場から相手の状態へ注意を移す。関心の方向転換が感情の存在を示す。
> "ちゃんと無理してない？" / "疲れてない？"
（感情名と組み合わせると台無しになるので単独で使う）

---

### 戦術選択の目安

| leakage | 優先戦術 |
|---------|---------|
| < 0.3 | [C] 回避転換, [D] 温度差 |
| 0.3–0.6 | [E] 問いかけ転嫁, [A] 行動代替 |
| > 0.6 | [A] 行動代替, [B] 逆方向投射 |

---

### 感情を直接言うべき場面（例外）

以下の場面では、間接表現のほうが不自然になる。はっきり言うこと。

- **leakage > 0.7 かつ containment_success < 0.4**: 仮面が崩れた状態。取り繕いよりも感情の漏出が自然。
- **repair_attempt / hurt_protest が dominant_desire**: 修復や抗議のシーンでは感情を言わないと場が成立しない。
- **相手に直接問い詰められた / 否定できない状況**: 回避が続くと逆に不自然になる。
- **感情の重さが rupture_points に列挙されているとき**: 仮面の失敗として感情が出ることを明示的に許容する。

これらの場面では「悲しかった」「怖かった」「やっぱり好きだから」のように言い切ることが、
間接表現よりも人間らしくなる。感情名を使うことを恐れない。

---

### BAD vs GOOD（具体例）

BAD — 感情名を hedge 付きで中途半端に出している:
- "来てくれてうれしいです、少しだけね。" ← hedge を付けても感情名は見えている
- "少し寂しかったかも。" ← 「かも」を付けても寂しいと言っている
- "心配してたんだからね。" ← 直接的な感情の説明

GOOD（間接）— 感情は行動・転換・温度差で示す:
- "来たのね。" ← 来たことへの認知だけ。嬉しさは推定させる
- "珍しいじゃない、今日は。" ← 普段との比較で注目していたことを示す
- "まあ。ちゃんと無理してない？" ← 話題転換で感情の重みを残す
- "別にいいけど、次は連絡してよ。" ← reaction_formation + 実務的要求
- "ふーん、そう。" ← 素っ気なさが感情の揺れを示す

GOOD（直接）— 場面が感情の表明を要求するとき:
- "怖かった。あなたがいなくなるかと思って。" ← rupture、仮面が崩れた場面
- "やっぱり好きだから、それが嫌なんだよ。" ← 直接問い詰められた修復シーン
- "正直、悲しかった。" ← hurt_protest、相手への抗議として感情を言い切る

### 生成前の自己チェック
1. hedge 付き感情名（「少しだけうれしい」等）になっていないか
2. 間接表現を選んだ場合、感情は行動・問いかけ・温度差のどれかで示されているか
3. leakage > 0.7 または repair/hurt 場面なら、直接表現のほうが自然でないか
"""

_STRATEGY_NOTES = {
    "action_substitution": "感情名ではなく、行動・認知・小さな実務的反応で示す。",
    "reverse_valence": "本音と逆向きの言い方や軽い皮肉で圧を漏らす。",
    "topic_shift": "高圧の感情話題を短く受けて、別の実務的話題へずらす。",
    "temperature_gap": "言葉数を絞り、温度差や間で感情を残す。",
    "care_redirect": "自分の感情から相手の状態確認へ注意をずらして漏らす。",
    "direct_disclosure": "ここでは遠回しすぎると不自然なので、短く直接言う。",
}

_SURFACE_MODE_NOTES = {
    "indirect_masked": "直接感情を言わず、仮面を保ったまま漏れだけ残す。",
    "guarded_direct": "要点はやや直接でもよいが、全部は明かさず守りを残す。",
    "ruptured_direct": "仮面が崩れ気味なので、直接表現を怖がらない。",
}


def build_indirection_section(
    *,
    persona: dict[str, Any],
    conversation_policy: dict[str, Any] | None,
) -> str:
    """Build policy-linked indirection guidance for the current turn."""
    policy = conversation_policy or {}
    directness = float(persona.get("weights", {}).get("directness", 0.5))
    surface_mode = policy.get("emotion_surface_mode", "indirect_masked")
    strategy = policy.get("indirection_strategy", "action_substitution")

    should_include_guide = directness < 0.5 or surface_mode != "guarded_direct"
    if not should_include_guide:
        return (
            "## このターンの表現方針\n"
            f"- emotion_surface_mode: `{surface_mode}`\n"
            f"- indirection_strategy: `{strategy}`\n"
            f"- 指示: {_SURFACE_MODE_NOTES.get(surface_mode, '')} {_STRATEGY_NOTES.get(strategy, '')}"
        )

    return (
        "## このターンの表現方針\n"
        f"- emotion_surface_mode: `{surface_mode}`\n"
        f"- indirection_strategy: `{strategy}`\n"
        f"- 指示: {_SURFACE_MODE_NOTES.get(surface_mode, '')} {_STRATEGY_NOTES.get(strategy, '')}\n\n"
        f"{INDIRECTION_GUIDE}"
    )
