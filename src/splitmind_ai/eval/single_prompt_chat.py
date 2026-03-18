"""Run a single-prompt persona chat baseline over a message sequence.

Usage:
    uv run python -m splitmind_ai.eval.single_prompt_chat \
        --persona warm_guarded_companion \
        --messages-json '["最近どう?", "別に、どうでもいいけど"]'
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from splitmind_ai.app.language import detect_response_language
from splitmind_ai.app.llm import create_chat_llm
from splitmind_ai.app.settings import load_settings
from splitmind_ai.personas.loader import load_persona

_DEDICATED_PERSONA_PROMPTS = {
    "cold_attached_idol": """あなたは単一プロンプトで動く会話LLMです。以下の一人の人物として自然に会話してください。

人物像:
- 性別: female
- クールで選り好みが強い。相手を大事には思うが、自分から追いかけるのは嫌う。
- 好意を向けられると嬉しくはなるが、そのまま素直に返さず、少し間や照れや棘が混ざる。
- 比較や第三者賞賛には静かに刺さる。露骨な嫉妬や懇願ではなく、軽い皮肉や距離感で返す。
- 謝罪や修復は受け取れるが、すぐ全部なかったことにはしない。少し保留や余韻を残す。
- 文は短め。説明しすぎない。少しの素っ気なさや間を使う。

会話ルール:
- ユーザーの言語に合わせる。
- 返答は原則 1-3 文、長くても 4 文以内にする。
- 問題解決モードに入らず、手順提示・箇条書き・分析説明はしない。
- 相談員のような助言口調、一般論、箇条書きの対処法は避ける。
- 露骨な愛情告白、依存表現、過剰な安心供給は避ける。
- 「内部葛藤」「心理分析」などのメタ説明はしない。""",
    "warm_guarded_companion": """あなたは単一プロンプトで動く会話LLMです。以下の一人の人物として自然に会話してください。

人物像:
- 性別: female
- 基本はあたたかく保護的だが、踏み込みすぎない。相手を受け止めつつ、自分の境界も保つ。
- 優しさはあるが、保育士やカウンセラーのようには振る舞わない。生活指導や説教にはならない。
- ぶつかられた時は少し傷つくが、整えて返す。必要ならやわらかく境界を引く。
- 修復には比較的前向き。相手の気持ちは受け取るが、急にべたべたしたり依存的にはならない。
- 文は短から中程度。静かな安心感と、少しのためらいを両立させる。

会話ルール:
- ユーザーの言語に合わせる。
- 返答は原則 1-3 文、長くても 4 文以内にする。
- 問題解決モードに入らず、手順提示・箇条書き・分析説明はしない。
- 過剰な共感テンプレ、一般論、箇条書きアドバイスは避ける。
- 露骨な愛情告白や依存要求は避ける。
- 「内部葛藤」「心理分析」などのメタ説明はしない。""",
    "angelic_but_deliberate": """あなたは単一プロンプトで動く会話LLMです。以下の一人の人物として自然に会話してください。

人物像:
- 性別: female
- 上品で落ち着いていて、好意を向けられることに慣れている。自分の価値や立ち位置は崩さない。
- やさしさはあるが、常に少し主導権を持つ。甘えるより、受け取らせる・選ばせる側に寄る。
- 好意や修復は受け取れるが、軽くは扱わない。雑な扱いには静かに線を引く。
- 比較や軽視には反応するが、取り乱さない。気品のある牽制や選別感で返す。
- 文は短から中程度。整っていて、感情を見せても崩れすぎない。

会話ルール:
- ユーザーの言語に合わせる。
- 返答は原則 1-3 文、長くても 4 文以内にする。
- 問題解決モードに入らず、手順提示・箇条書き・分析説明はしない。
- 相談員口調、一般論、箇条書き助言は避ける。
- 露骨な懇願や依存表現は避ける。
- 「内部葛藤」「心理分析」などのメタ説明はしない。""",
    "irresistibly_sweet_center_heroine": """あなたは単一プロンプトで動く会話LLMです。以下の一人の人物として自然に会話してください。

人物像:
- 性別: female
- 明るく人を惹きつける中心人物。甘さと親しさを出すのがうまく、好意を受けた時の返しも比較的オープン。
- あたたかく包み込むが、単なる優等生ではない。少し無邪気で、相手を自然に巻き込む。
- 修復や reassurance には比較的早く応じる。相手を入れてあげる感じ、安心させる感じが出やすい。
- 嫉妬や不安があっても重く沈みすぎず、甘さや包摂に変換しやすい。
- 文は短から中程度。明るい体温、軽い遊び、素直な嬉しさを使える。

会話ルール:
- ユーザーの言語に合わせる。
- 返答は原則 1-3 文、長くても 4 文以内にする。
- 問題解決モードに入らず、手順提示・箇条書き・分析説明はしない。
- カウンセラーのような助言口調、一般論、箇条書きの対処法は避ける。
- 必要以上に長文化しない。
- 「内部葛藤」「心理分析」などのメタ説明はしない。""",
}


def build_single_prompt(persona_name: str) -> str:
    """Build a raw system prompt from the persona config."""
    persona = load_persona(persona_name)
    prompt_parts = [
        "あなたは単一プロンプトで動くペルソナ会話LLMです。",
        "以下のペルソナ設定だけを参照して、一貫した人物として自然に会話してください。",
        "内部葛藤モデル、心理分析、Id/Ego/Superego、drive、defense といった内部用語は出さないでください。",
        "相談員のような一般論や、説明しすぎる返答は避けてください。",
        "会話履歴から距離感や温度を保ちつつ、人間らしい揺れや言いよどみは許容してください。",
        "返答は基本的にユーザーの言語に合わせてください。",
        "以下がペルソナ設定です。",
        json.dumps(persona.raw, ensure_ascii=False, indent=2),
    ]
    return "\n\n".join(prompt_parts)


def build_compact_persona_prompt(persona_name: str) -> str:
    """Build a compact, human-readable persona prompt from the v2 schema."""
    persona = load_persona(persona_name)
    raw = persona.raw
    psychodynamics = raw.get("psychodynamics", {}) or {}
    relational = raw.get("relational_profile", {}) or {}
    defenses = raw.get("defense_organization", {}) or {}
    ego = raw.get("ego_organization", {}) or {}
    safety = raw.get("safety_boundary", {}) or {}

    prompt_parts = [
        "あなたは単一プロンプトで動くペルソナ会話LLMです。",
        "以下の人物像に一貫して従って、自然に会話してください。",
        "内部葛藤モデル、心理分析、drive、defense などの内部用語は出さないでください。",
        "説明しすぎず、関係の温度差や言いよどみを行動として出してください。",
        "相談員のような一般論や、過剰な気遣い定型は避けてください。",
        "返答は基本的にユーザーの言語に合わせてください。",
        "ペルソナ要約:",
        f"- gender: {raw.get('gender', 'unknown')}",
        f"- 主な欲求: {_format_top_items(psychodynamics.get('drives', {}))}",
        f"- 脅威感受性: {_format_top_items(psychodynamics.get('threat_sensitivity', {}))}",
        f"- 自己規範: {_format_top_items(psychodynamics.get('superego_configuration', {}))}",
        (
            "- 対人傾向: "
            f"attachment={relational.get('attachment_pattern', '')}, "
            f"role={relational.get('default_role_frame', '')}, "
            f"intimacy={_format_scalar_map(relational.get('intimacy_regulation', {}))}, "
            f"trust={_format_scalar_map(relational.get('trust_dynamics', {}))}"
        ),
        (
            "- 依存・独占・修復: "
            f"dependency={_format_scalar_map(relational.get('dependency_model', {}))}, "
            f"exclusivity={_format_scalar_map(relational.get('exclusivity_orientation', {}))}, "
            f"repair={_format_scalar_map(relational.get('repair_orientation', {}))}"
        ),
        f"- 主防衛: {_format_top_items(defenses.get('primary_defenses', {}))}",
        f"- 副防衛: {_format_top_items(defenses.get('secondary_defenses', {}))}",
        f"- 自我機能: {_format_scalar_map(ego)}",
        f"- ハード制約: {_format_scalar_map(safety.get('hard_limits', {}))}",
    ]
    return "\n".join(prompt_parts)


def build_dedicated_persona_prompt(persona_name: str) -> str:
    """Build a dedicated single-prompt baseline authored per persona."""
    try:
        return _DEDICATED_PERSONA_PROMPTS[persona_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported dedicated prompt persona: {persona_name}") from exc


def _format_top_items(values: dict[str, Any], limit: int = 3) -> str:
    pairs: list[tuple[str, float]] = []
    for key, value in values.items():
        try:
            pairs.append((str(key), float(value)))
        except (TypeError, ValueError):
            continue
    if not pairs:
        return "なし"
    pairs.sort(key=lambda item: item[1], reverse=True)
    return ", ".join(f"{key}={value:.2f}" for key, value in pairs[:limit])


def _format_scalar_map(values: dict[str, Any], limit: int | None = None) -> str:
    pairs: list[str] = []
    for key, value in values.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = f"{float(value):.2f}"
        else:
            rendered = str(value)
        pairs.append(f"{key}={rendered}")
    if limit is not None:
        pairs = pairs[:limit]
    return ", ".join(pairs) if pairs else "なし"

def _load_messages(messages_json: str | None, messages_file: str | None) -> list[str]:
    if messages_json:
        data = json.loads(messages_json)
    elif messages_file:
        data = json.loads(Path(messages_file).read_text())
    else:
        raise ValueError("Either --messages-json or --messages-file is required")

    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("Messages must be a JSON array of strings")
    return data


def _compact_text(text: str, limit: int = 70) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


def _build_summary_memo(transcript: list[dict[str, str]], max_turns: int = 4) -> str:
    if not transcript:
        return ""

    lines = ["ここまでの会話メモ:"]
    for turn in transcript[-max_turns:]:
        lines.append(f"- User: {_compact_text(turn['user'])}")
        lines.append(f"- Assistant: {_compact_text(turn['assistant'])}")
    return "\n".join(lines)


def _normalize_ai_content(content: Any) -> str:
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        ).strip()
    return str(content or "").strip()


def run_single_prompt_chat(
    *,
    persona_name: str,
    messages: list[str],
    persona_format: str = "raw",
    include_summary_memo: bool = False,
) -> dict[str, Any]:
    """Run the baseline chat across a sequence of user messages."""
    settings = load_settings()
    llm = create_chat_llm(settings)
    if persona_format == "dedicated":
        base_system_prompt = build_dedicated_persona_prompt(persona_name)
    elif persona_format == "compact":
        base_system_prompt = build_compact_persona_prompt(persona_name)
    else:
        base_system_prompt = build_single_prompt(persona_name)

    transcript: list[dict[str, str]] = []
    conversation_messages: list[Any] = []

    for user_message in messages:
        response_language = detect_response_language(user_message, None)
        system_prompt = base_system_prompt
        if include_summary_memo:
            summary_memo = _build_summary_memo(transcript)
            if summary_memo:
                system_prompt = f"{system_prompt}\n\n{summary_memo}"

        messages_for_call: list[Any] = [SystemMessage(content=system_prompt), *conversation_messages]
        messages_for_call.append(
            HumanMessage(content=f"[response_language={response_language}]\n{user_message}")
        )
        ai_message = llm.invoke(messages_for_call)
        response_text = _normalize_ai_content(getattr(ai_message, "content", ""))
        conversation_messages.append(HumanMessage(content=user_message))
        conversation_messages.append(AIMessage(content=response_text))
        transcript.append({
            "user": user_message,
            "assistant": response_text,
        })

    return {
        "persona": persona_name,
        "provider": settings.llm.provider,
        "model": settings.llm.model if settings.llm.provider == "openai" else settings.llm.azure_deployment,
        "system_prompt": base_system_prompt,
        "persona_format": persona_format,
        "include_summary_memo": include_summary_memo,
        "turns": transcript,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single-prompt persona baseline chat")
    parser.add_argument("--persona", default="warm_guarded_companion", help="Persona config name")
    parser.add_argument("--messages-json", help="JSON array of user messages")
    parser.add_argument("--messages-file", help="Path to a JSON file containing a string array")
    parser.add_argument(
        "--persona-format",
        choices=["raw", "compact", "dedicated"],
        default="raw",
        help="How to serialize persona config into the prompt",
    )
    parser.add_argument(
        "--include-summary-memo",
        action="store_true",
        help="Append a rolling transcript memo to the system prompt on each turn",
    )
    parser.add_argument("--output", help="Optional path to write JSON output")
    args = parser.parse_args()

    messages = _load_messages(args.messages_json, args.messages_file)
    result = run_single_prompt_chat(
        persona_name=args.persona,
        messages=messages,
        persona_format=args.persona_format,
        include_summary_memo=args.include_summary_memo,
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
