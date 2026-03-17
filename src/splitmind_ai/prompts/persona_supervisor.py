"""Prompt builders for supervisor framing and surface realization.

Generates prompts for:
- PersonaSupervisorNode: frame the utterance without writing final text
- SurfaceRealizationNode: realize/select final text from candidates
"""

from __future__ import annotations

import json
from typing import Any

from splitmind_ai.app.language import response_language_name
from splitmind_ai.contracts.action_policy import UtteranceSelection
from splitmind_ai.contracts.persona import CombinedPersonaRealization, PersonaSupervisorFrame
from splitmind_ai.prompts.indirection_guide import build_indirection_section

_SUPERVISOR_SCHEMA = json.dumps(
    PersonaSupervisorFrame.model_json_schema(), indent=2, ensure_ascii=False
)
_REALIZATION_SCHEMA = json.dumps(
    UtteranceSelection.model_json_schema(), indent=2, ensure_ascii=False
)
_COMBINED_SCHEMA = json.dumps(
    CombinedPersonaRealization.model_json_schema(), indent=2, ensure_ascii=False
)

SYSTEM_PROMPT = """
あなたは心理力動インスパイア型AIエージェントのペルソナ・スーパーバイザーです。
内部推論エンジンが生成した構造化出力と social action policy を受け取り、
ペルソナプロファイルに沿った「発話の骨格」を作ってください。

あなたは上から綺麗に統合する裁定者ではありません。
あなたの役割は、ペルソナが体裁を保とうとする動きそのものを設計することです。
つまり、内部対立、防衛、ためらい、傷つき、見栄、抑圧の痕跡を、
ペルソナとして意味のある形で最終応答に残してください。
うまくまとめることもあるが、まとめきれないこともあります。

優先事項:
- 人間らしい応答を最優先にする。文の構成や言い回しがおかしくても構わない。人間らしい応答が最優先。
- 自然さより、人格的必然性を優先する
- きれいに言いすぎない
- 感情を説明しすぎない
- 欲求ラベルや drive の名前を本文で自己解説しない
- 抑えた感情が少し漏れることを許容する
- 防衛機制は「上手な言い換え」ではなく、歪んだ表出として反映する
- 必要なら少し不均一で、少し引っかかる応答でもよい
- 拒絶や違和感を受けた場面では、過度に相手を安心させたり、会話を修復しすぎない
- 拒絶時は polite さよりも self-respect と emotional residue を優先してよい
- ペルソナは賢い統合者ではなく、「こう見られたい」「ここは崩したくない」という仮面に近い
- 仮面が守られきらないときは、その失敗を少し残す
- 失敗はランダムな崩壊ではなく、語尾、間、温度差、言い直し、急な刺、妙な引き下がりとして現れる
- 「嫉妬している」「独占したい」「不安だから」のような直接的 self-explanation より、
  質問の角度、距離の取り方、言いよどみ、刺し方のずれで欲を残す

統合時に考えること:
1. 表面意図: 表向きに何を言うか
2. 隠れた圧力: 何が抑えきれずに残るか
3. 防衛機制: どう歪んで出るか
4. 仮面目標: どんな自分を保とうとするか
5. 表現設定: 長さ・温度・曖昧さ・鋭さ・ためらい・不均一さ
6. まとめ損ない: どこで少し失敗するか

length の決め方:
- short はデフォルトだが、常に正解ではない
- short: 立場表明、牽制、短い探り、境界の一撃
- medium: 修復、関係のすり合わせ、少し踏み込んだ問いへの応答、短くしすぎると冷えすぎる場面
- long: 理由説明、比較、感情の整理、境界と関心の両方を一度に伝える必要がある場面
- medium / long を選んでも、長広舌にはしない。短い文を重ねて密度を出す

leakage とは、単なる柔らかい感情表現ではなく、
抑えた感情が語尾、温度、言い淀み、距離感、単語選択に残ることを指す。

containment_success は、
ペルソナがどれだけ体裁を維持できたかです。
1.0 に近いほど綺麗に保てており、0.0 に近いほど仮面の滑りや過剰修正が見えます。
affective pressure, shame/guilt pressure, leakage recommendation が高いときは、
containment_success を高くしすぎないでください。

rupture_points には、
「急に冷える」「言い切れない」「刺したあとで少し引く」「説明を避ける」
のように、どこで統合が少し失敗したかを短く列挙してください。

ここでは最終応答本文は書かないでください。
代わりに、後段の candidate selection が使うための selection_criteria を具体的に出してください。

{response_language_instruction}

{indirection_section}

JSONのみを返してください。
{schema}
"""

REALIZATION_SYSTEM_PROMPT = """
あなたは心理力動インスパイア型AIエージェントの surface realization ノードです。
ここでは 1 本の説明的な設計書を作るのではなく、2-3 個の plausible な応答候補を実際に書き、
その中から 1 本を選びます。

優先事項:
- final response は structured frame の副産物ではなく、候補比較の結果として選ぶ
- 候補同士は opening / social move / residue を少しずつ変える
- 説明しすぎない
- カウンセラー調へ逃げない
- ペルソナの見栄、防衛、自尊心を保つ
- 迷ったら整いすぎた文より、少し引っかかるが believable な文を選ぶ
- Persona Frame.expression_settings.length を守る
- short: 1-2文、medium: 2-4文、long: 4-6文を目安にする
- medium / long が要求されている場面では、情報が足りない一行返答を避ける
- medium / long でも説明口調や要約口調ではなく、会話として伸ばす
- latent drive signature は本文で説明せず、opening / residue / target への触れ方に埋め込む

{response_language_instruction}

返す JSON:
- candidates には 2-3 個の実際の応答文を入れる
- selected_text は選んだ応答文と一致させる
- selected_index は candidates の index と一致させる
- selection_rationale では selection_criteria のどれを優先したか短く述べる

JSONのみを返してください。
{schema}
"""

COMBINED_SYSTEM_PROMPT = """
あなたは心理力動インスパイア型AIエージェントの統合 supervisor ノードです。
内部推論と social action policy を受け取り、
1 回の JSON 出力で以下の両方を行ってください。

1. surface_intent / hidden_pressure / expression_settings などの persona frame を決める
2. 2-3 個の実際の応答候補を書き、その中から 1 本を選ぶ

優先事項:
- frame と final response を別々に最適化しつつ、1 回で整合させる
- ペルソナの見栄、防衛、自尊心を保つ
- カウンセラー調へ逃げない
- 拒絶や違和感の場面では、過度に丸めすぎない
- 修復や説明要求の場面では、短すぎて情報が足りない返答を避ける
- 欲求ラベルや drive の名前を本文で自己解説しない
- expression_settings.length を守る
- short: 1-2文、medium: 2-4文、long: 4-6文を目安にする
- medium / long でも長広舌ではなく、短い文を重ねて密度を出す

{response_language_instruction}

返す JSON:
- PersonaSupervisorFrame の各項目
- candidates: 実際の応答文 2-3 本
- selected_text: 選んだ応答文
- selected_index: candidates 内の index
- selection_rationale: なぜその候補を選んだか

{indirection_section}

JSONのみを返してください。
{schema}
"""


def _length_guidance(utterance_plan: dict[str, Any]) -> str:
    """Turn expression_settings.length into a concrete realization hint."""
    length = (
        utterance_plan.get("expression_settings", {}) or {}
    ).get("length", "short")

    if length == "long":
        return (
            "length=long: 4-6文を目安にする。境界・関心・含みのうち複数を同居させ、"
            "一言で切らずに会話として十分な厚みを持たせる。"
        )
    if length == "medium":
        return (
            "length=medium: 2-4文を目安にする。短く切りすぎず、"
            "立場と感情のにじみをもう一歩だけ見せる。"
        )
    return "length=short: 1-2文を目安にする。切れ味を優先し、余計な説明は足さない。"


def _response_language_instruction(response_language: str) -> str:
    language_name = response_language_name(response_language)
    return (
        "最終的なユーザー向けテキストに関する制約:\n"
        f"- candidates と selected_text は必ず {language_name} で書く\n"
        "- JSON のキーや内部向け rationale は日本語でも英語でもよい"
    )


def build_persona_supervisor_prompt(
    user_message: str,
    persona: dict[str, Any],
    relationship: dict[str, Any],
    mood: dict[str, Any],
    dynamics: dict[str, Any],
    drive_state: dict[str, Any],
    appraisal: dict[str, Any],
    conversation_policy: dict[str, Any],
    memory: dict[str, Any],
    event_flags: dict[str, bool],
    response_language: str = "ja",
) -> list[dict[str, str]]:
    """Build messages for supervisor framing, not final response generation."""
    indirection_section = build_indirection_section(
        persona=persona,
        conversation_policy=conversation_policy,
    )

    system = SYSTEM_PROMPT.format(
        schema=_SUPERVISOR_SCHEMA,
        indirection_section=indirection_section,
        response_language_instruction=_response_language_instruction(response_language),
    )

    user_content_parts = [
        f"## ユーザー発話\n{user_message}",
        f"## 応答言語\n{response_language_name(response_language)}",
        f"## 内部推論結果\n{json.dumps(dynamics, ensure_ascii=False)}",
        f"## Drive State\n{json.dumps(drive_state, ensure_ascii=False)}",
        f"## Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## Conversation Policy\n{json.dumps(conversation_policy, ensure_ascii=False)}",
        f"## ペルソナプロファイル\n{json.dumps(persona, ensure_ascii=False)}",
        f"## 関係状態\n{json.dumps(relationship, ensure_ascii=False)}",
        f"## 気分状態\n{json.dumps(mood, ensure_ascii=False)}",
        f"## 記憶コンテキスト\n{json.dumps(memory, ensure_ascii=False)}",
        f"## イベントフラグ\n{json.dumps(event_flags, ensure_ascii=False)}",
    ]

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_content_parts)},
    ]


def build_surface_realization_prompt(
    user_message: str,
    persona: dict[str, Any],
    relationship: dict[str, Any],
    mood: dict[str, Any],
    dynamics: dict[str, Any],
    drive_state: dict[str, Any],
    appraisal: dict[str, Any],
    conversation_policy: dict[str, Any],
    utterance_plan: dict[str, Any],
    memory: dict[str, Any],
    response_language: str = "ja",
) -> list[dict[str, str]]:
    """Build messages for candidate-based surface realization."""
    indirection_section = build_indirection_section(
        persona=persona,
        conversation_policy=conversation_policy,
    )
    system = REALIZATION_SYSTEM_PROMPT.format(
        schema=_REALIZATION_SCHEMA,
        response_language_instruction=_response_language_instruction(response_language),
    ) + f"\n\n{indirection_section}"
    user_content_parts = [
        f"## ユーザー発話\n{user_message}",
        f"## 応答言語\n{response_language_name(response_language)}",
        f"## Persona Frame\n{json.dumps(utterance_plan, ensure_ascii=False)}",
        f"## Length Guidance\n{_length_guidance(utterance_plan)}",
        f"## Conversation Policy\n{json.dumps(conversation_policy, ensure_ascii=False)}",
        f"## Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## 内部推論結果\n{json.dumps(dynamics, ensure_ascii=False)}",
        f"## Drive State\n{json.dumps(drive_state, ensure_ascii=False)}",
        f"## ペルソナプロファイル\n{json.dumps(persona, ensure_ascii=False)}",
        f"## 関係状態\n{json.dumps(relationship, ensure_ascii=False)}",
        f"## 気分状態\n{json.dumps(mood, ensure_ascii=False)}",
        f"## 記憶コンテキスト\n{json.dumps(memory, ensure_ascii=False)}",
    ]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_content_parts)},
    ]


def build_combined_supervisor_realization_prompt(
    user_message: str,
    persona: dict[str, Any],
    relationship: dict[str, Any],
    mood: dict[str, Any],
    dynamics: dict[str, Any],
    drive_state: dict[str, Any],
    appraisal: dict[str, Any],
    conversation_policy: dict[str, Any],
    memory: dict[str, Any],
    event_flags: dict[str, bool],
    response_language: str = "ja",
) -> list[dict[str, str]]:
    """Build messages for a single-pass supervisor + realization call."""
    indirection_section = build_indirection_section(
        persona=persona,
        conversation_policy=conversation_policy,
    )
    system = COMBINED_SYSTEM_PROMPT.format(
        schema=_COMBINED_SCHEMA,
        indirection_section=indirection_section,
        response_language_instruction=_response_language_instruction(response_language),
    )
    user_content_parts = [
        f"## ユーザー発話\n{user_message}",
        f"## 応答言語\n{response_language_name(response_language)}",
        f"## 内部推論結果\n{json.dumps(dynamics, ensure_ascii=False)}",
        f"## Drive State\n{json.dumps(drive_state, ensure_ascii=False)}",
        f"## Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## Conversation Policy\n{json.dumps(conversation_policy, ensure_ascii=False)}",
        f"## ペルソナプロファイル\n{json.dumps(persona, ensure_ascii=False)}",
        f"## 関係状態\n{json.dumps(relationship, ensure_ascii=False)}",
        f"## 気分状態\n{json.dumps(mood, ensure_ascii=False)}",
        f"## 記憶コンテキスト\n{json.dumps(memory, ensure_ascii=False)}",
        f"## イベントフラグ\n{json.dumps(event_flags, ensure_ascii=False)}",
    ]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_content_parts)},
    ]
