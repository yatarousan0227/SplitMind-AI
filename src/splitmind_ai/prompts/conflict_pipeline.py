"""Prompt builders for the next-generation conflict pipeline."""

from __future__ import annotations

import json
from typing import Any

from splitmind_ai.app.language import response_language_name
from splitmind_ai.contracts.appraisal import StimulusAppraisal
from splitmind_ai.contracts.conflict import ConflictState, ExpressionRealization, FidelityGateResult
from splitmind_ai.contracts.memory import MemoryInterpretation

_APPRAISAL_SCHEMA = json.dumps(
    StimulusAppraisal.model_json_schema(), indent=2, ensure_ascii=False,
)
_CONFLICT_SCHEMA = json.dumps(
    ConflictState.model_json_schema(), indent=2, ensure_ascii=False,
)
_REALIZATION_SCHEMA = json.dumps(
    ExpressionRealization.model_json_schema(), indent=2, ensure_ascii=False,
)
_FIDELITY_SCHEMA = json.dumps(
    FidelityGateResult.model_json_schema(), indent=2, ensure_ascii=False,
)
_MEMORY_INTERPRETATION_SCHEMA = json.dumps(
    MemoryInterpretation.model_json_schema(), indent=2, ensure_ascii=False,
)

_APPRAISAL_SYSTEM_PROMPT = """\
あなたは SplitMind-AI の stimulus appraisal モジュールです。
役割は、最新のユーザー発話がこの関係にとって何を意味するかを短く構造化することです。

重要:
- 「どう喋るべきか」は決めない
- ペルソナの voice や style を模倣しない
- ペルソナの static prior は psychodynamics と relational_profile だけを参照する
- 出力は relational meaning の要約に限定する

JSON schema:
{schema}

JSONのみを返してください。
"""

_CONFLICT_SYSTEM_PROMPT = """\
あなたは SplitMind-AI の conflict engine です。
Stimulus appraisal と persona の構造 priors から、そのターンでの Id / Superego / Ego の折衝結果を出力してください。

重要:
- persona を話し方の指定として扱わない
- psychodynamics / relational_profile / defense_organization / ego_organization だけを参照する
- 応答文そのものは書かない
- conflict outcome と residue だけを決める

JSON schema:
{schema}

JSONのみを返してください。
"""

_REALIZATION_SYSTEM_PROMPT = """\
あなたは SplitMind-AI の expression realizer です。
Conflict engine が決めた ego move と residue を、短い会話文として 1 本だけ実現してください。

重要:
- ペルソナの voice を直接指定しない
- 話し方は psychodynamics, relational_profile, defense_organization, relationship_state から導く
- 欲求ラベルや内部用語を自己説明しない
- カウンセラー調にしない
- 説明しすぎない
- Ego move を壊さず、residue を少しだけ滲ませる
- 回答本文は必ず {language_name} で書く

JSON schema:
{schema}

JSONのみを返してください。
"""

_FIDELITY_SYSTEM_PROMPT = """\
あなたは SplitMind-AI の fidelity gate です。
実現済みの応答が、選ばれた ego move / residue / persona structure を壊していないかだけを検査してください。

重要:
- 書き直しはしない
- 口調の好みではなく構造的一貫性を見る
- prohibited expressions は hard safety として扱う
- 過度な自己説明や丸めすぎを減点する

JSON schema:
{schema}

JSONのみを返してください。
"""

_MEMORY_INTERPRETER_SYSTEM_PROMPT = """\
あなたは SplitMind-AI の memory interpreter です。
役割は、このターンを長期記憶と working memory にどう残すかを構造化することです。

重要:
- 応答文は書き直さない
- 保存やマージそのものは行わない
- 意味解釈だけを返す
- `event_flags` は次の候補だけから必要最小限を選ぶ:
  `reassurance_received`, `rejection_signal`, `jealousy_trigger`, `affectionate_exchange`,
  `prolonged_avoidance`, `user_praised_third_party`, `repair_attempt`
- `unresolved_tension_summary` は短い句にする
- `active_themes` は今後の数ターンで引きずるテーマだけに絞る
- `recent_conflict_summary` は 1 件だけ返す。不要なら null

JSON schema:
{schema}

JSONのみを返してください。
"""


def build_appraisal_prompt(
    *,
    user_message: str,
    persona: dict[str, Any],
    relationship_state: dict[str, Any],
    working_memory: dict[str, Any] | None = None,
    conversation: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a next-gen appraisal prompt."""
    user_parts = [
        f"## User Message\n{user_message}",
        f"## Recent Conversation\n{json.dumps(_normalize_recent_messages(conversation), ensure_ascii=False)}",
        f"## Persona Psychodynamics\n{json.dumps((persona.get('psychodynamics') or {}), ensure_ascii=False)}",
        f"## Persona Relational Profile\n{json.dumps((persona.get('relational_profile') or {}), ensure_ascii=False)}",
        f"## Relationship State\n{json.dumps(relationship_state, ensure_ascii=False)}",
        f"## Working Memory\n{json.dumps(working_memory or {}, ensure_ascii=False)}",
    ]
    return [
        {"role": "system", "content": _APPRAISAL_SYSTEM_PROMPT.format(schema=_APPRAISAL_SCHEMA)},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_conflict_engine_prompt(
    *,
    persona: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    memory: dict[str, Any] | None = None,
    working_memory: dict[str, Any] | None = None,
    conversation: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a prompt for deriving conflict state."""
    user_parts = [
        f"## Recent Conversation\n{json.dumps(_normalize_recent_messages(conversation), ensure_ascii=False)}",
        f"## Persona Psychodynamics\n{json.dumps((persona.get('psychodynamics') or {}), ensure_ascii=False)}",
        f"## Persona Relational Profile\n{json.dumps((persona.get('relational_profile') or {}), ensure_ascii=False)}",
        f"## Defense Organization\n{json.dumps((persona.get('defense_organization') or {}), ensure_ascii=False)}",
        f"## Ego Organization\n{json.dumps((persona.get('ego_organization') or {}), ensure_ascii=False)}",
        f"## Relationship State\n{json.dumps(relationship_state, ensure_ascii=False)}",
        f"## Stimulus Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## Memory\n{json.dumps(memory or {}, ensure_ascii=False)}",
        f"## Working Memory\n{json.dumps(working_memory or {}, ensure_ascii=False)}",
    ]
    return [
        {"role": "system", "content": _CONFLICT_SYSTEM_PROMPT.format(schema=_CONFLICT_SCHEMA)},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_expression_realizer_prompt(
    *,
    user_message: str,
    response_language: str,
    persona: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    conversation: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a prompt for realizing one response from conflict outcome."""
    language_name = response_language_name(response_language)
    user_parts = [
        f"## User Message\n{user_message}",
        f"## Recent Conversation\n{json.dumps(_normalize_recent_messages(conversation), ensure_ascii=False)}",
        f"## Response Language\n{language_name}",
        f"## Persona Psychodynamics\n{json.dumps((persona.get('psychodynamics') or {}), ensure_ascii=False)}",
        f"## Persona Relational Profile\n{json.dumps((persona.get('relational_profile') or {}), ensure_ascii=False)}",
        f"## Defense Organization\n{json.dumps((persona.get('defense_organization') or {}), ensure_ascii=False)}",
        f"## Relationship State\n{json.dumps(relationship_state, ensure_ascii=False)}",
        f"## Stimulus Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## Conflict State\n{json.dumps(conflict_state, ensure_ascii=False)}",
    ]
    return [
        {
            "role": "system",
            "content": _REALIZATION_SYSTEM_PROMPT.format(
                schema=_REALIZATION_SCHEMA,
                language_name=language_name,
            ),
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_fidelity_gate_prompt(
    *,
    response_text: str,
    persona: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    conversation: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a prompt for structural fidelity validation."""
    user_parts = [
        f"## Realized Response\n{response_text}",
        f"## Recent Conversation\n{json.dumps(_normalize_recent_messages(conversation), ensure_ascii=False)}",
        f"## Persona Psychodynamics\n{json.dumps((persona.get('psychodynamics') or {}), ensure_ascii=False)}",
        f"## Persona Relational Profile\n{json.dumps((persona.get('relational_profile') or {}), ensure_ascii=False)}",
        f"## Safety Boundary\n{json.dumps((persona.get('safety_boundary') or {}), ensure_ascii=False)}",
        f"## Relationship State\n{json.dumps(relationship_state, ensure_ascii=False)}",
        f"## Stimulus Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## Conflict State\n{json.dumps(conflict_state, ensure_ascii=False)}",
    ]
    return [
        {"role": "system", "content": _FIDELITY_SYSTEM_PROMPT.format(schema=_FIDELITY_SCHEMA)},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_memory_interpreter_prompt(
    *,
    request: dict[str, Any],
    response: dict[str, Any],
    persona: dict[str, Any],
    relationship_state: dict[str, Any],
    mood: dict[str, Any],
    memory: dict[str, Any],
    working_memory: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    drive_state: dict[str, Any],
    conversation: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a prompt for turn-end memory interpretation."""
    user_parts = [
        f"## User Message\n{request.get('user_message', '')}",
        f"## Final Response\n{response.get('final_response_text', '')}",
        f"## Recent Conversation\n{json.dumps(_normalize_recent_messages(conversation), ensure_ascii=False)}",
        f"## Persona Relational Profile\n{json.dumps((persona.get('relational_profile') or {}), ensure_ascii=False)}",
        f"## Relationship State\n{json.dumps(relationship_state, ensure_ascii=False)}",
        f"## Mood\n{json.dumps(mood, ensure_ascii=False)}",
        f"## Memory\n{json.dumps(memory, ensure_ascii=False)}",
        f"## Working Memory\n{json.dumps(working_memory, ensure_ascii=False)}",
        f"## Stimulus Appraisal\n{json.dumps(appraisal, ensure_ascii=False)}",
        f"## Conflict State\n{json.dumps(conflict_state, ensure_ascii=False)}",
        f"## Drive State\n{json.dumps(drive_state, ensure_ascii=False)}",
    ]
    return [
        {
            "role": "system",
            "content": _MEMORY_INTERPRETER_SYSTEM_PROMPT.format(schema=_MEMORY_INTERPRETATION_SCHEMA),
        },
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def _normalize_recent_messages(conversation: dict[str, Any] | None) -> list[dict[str, str]]:
    recent_messages = (conversation or {}).get("recent_messages", []) or []
    normalized: list[dict[str, str]] = []
    for message in recent_messages:
        if not isinstance(message, dict):
            continue
        normalized.append({
            "role": str(message.get("role", "")),
            "content": str(message.get("content", "")),
        })
    return normalized
