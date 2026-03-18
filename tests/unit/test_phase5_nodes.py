"""Targeted tests for phase-5 prompt-backed realization nodes."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.nodes.appraisal import AppraisalNode
from splitmind_ai.nodes.conflict_engine import ConflictEngineNode
from splitmind_ai.nodes.expression_realizer import ExpressionRealizerNode
from splitmind_ai.nodes.fidelity_gate import FidelityGateNode
from splitmind_ai.nodes.memory_interpreter import MemoryInterpreterNode


class _FakeStructuredLLM:
    def __init__(self, payload: dict):
        self._payload = payload
        self._schema = None

    def with_structured_output(self, schema, method: str | None = None):
        self._schema = schema
        return self

    async def ainvoke(self, messages):
        return self._schema.model_validate(self._payload)


@pytest.mark.asyncio
async def test_appraisal_uses_llm_structured_output_with_conversation_context():
    node = AppraisalNode(
        llm=_FakeStructuredLLM({
            "event_type": "boundary_test",
            "valence": "mixed",
            "target_of_tension": "control",
            "stakes": "medium",
            "confidence": 0.84,
            "cues": [
                {
                    "label": "timing_pushback",
                    "evidence": "今は話さないの？",
                    "intensity": 0.72,
                    "confidence": 0.81,
                }
            ],
            "summary_short": "User pushes back on deferral and wants immediate contact.",
            "user_intent_guess": "seek_immediate_contact",
            "active_themes": ["contact", "timing"],
        })
    )
    inputs = NodeInputs(
        request={"user_message": "今は話さないの？"},
        persona={
            "psychodynamics": {"drives": {"closeness": 0.8}},
            "relational_profile": {"attachment_pattern": "anxious_avoidant_mixed"},
        },
        relationship_state={"durable": {"trust": 0.52}, "ephemeral": {"tension": 0.18}},
        working_memory={"active_themes": ["contact", "timing"]},
        conversation={
            "recent_messages": [
                {"role": "user", "content": "僕も元気！"},
                {"role": "assistant", "content": "よかった、少し安心した。無理しすぎず、また話そう。"},
            ]
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["appraisal"]["event_type"] == "boundary_test"
    assert state["appraisal"]["target_of_tension"] == "control"
    assert state["appraisal"]["user_intent_guess"] == "seek_immediate_contact"
    assert state["trace"]["appraisal"]["used_llm"] is True


@pytest.mark.asyncio
async def test_expression_realizer_prefers_llm_output_when_available():
    node = ExpressionRealizerNode(
        llm=_FakeStructuredLLM({
            "text": "…そう。そこまで言うなら、少しは信じる。",
            "rationale_short": "Keep the boundary but soften slightly.",
            "move_alignment": "accept_but_hold",
            "residue_handling": "guarded warmth",
        })
    )
    inputs = NodeInputs(
        request={"user_message": "ごめん、さっきは言い過ぎた", "response_language": "ja"},
        persona={
            "psychodynamics": {},
            "relational_profile": {},
            "defense_organization": {},
        },
        relationship_state={"durable": {"trust": 0.62}, "ephemeral": {"tension": 0.18}},
        appraisal={"event_type": "repair_offer"},
        conflict_state={
            "ego_move": {"social_move": "accept_but_hold"},
            "residue": {"visible_emotion": "pleased_but_guarded"},
            "expression_envelope": {"length": "short", "temperature": "cool_warm", "directness": 0.4, "closure": 0.4},
        },
        mood={},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["final_response_text"] == "…そう。そこまで言うなら、少しは信じる。"
    assert state["trace"]["expression_realizer"]["used_llm"] is True


@pytest.mark.asyncio
async def test_expression_realizer_fallback_does_not_use_identity_labels():
    node = ExpressionRealizerNode(llm=None)
    inputs = NodeInputs(
        request={"user_message": "ねえ", "response_language": "en"},
        persona={
            "psychodynamics": {},
            "relational_profile": {},
            "defense_organization": {},
        },
        relationship_state={"durable": {"trust": 0.2}, "ephemeral": {"tension": 0.1}},
        appraisal={"event_type": "casual_check_in"},
        conflict_state={
            "ego_move": {"social_move": "unknown_move"},
            "residue": {"visible_emotion": "neutral"},
            "expression_envelope": {"length": "short", "temperature": "cool", "directness": 0.2, "closure": 0.6},
        },
        mood={},
        conversation={"recent_messages": []},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["final_response_text"] == "...Right. If you want to keep talking, do it a little more honestly."
    assert state["trace"]["expression_realizer"]["used_llm"] is False


@pytest.mark.asyncio
async def test_conflict_engine_uses_llm_structured_output():
    node = ConflictEngineNode(
        llm=_FakeStructuredLLM({
            "id_impulse": {
                "dominant_want": "move_closer",
                "secondary_wants": ["preserve_status"],
                "intensity": 0.73,
                "target": "user",
            },
            "superego_pressure": {
                "forbidden_moves": ["direct_neediness"],
                "self_image_to_protect": "composed_and_self_respecting",
                "pressure": 0.77,
                "shame_load": 0.41,
            },
            "ego_move": {
                "social_move": "accept_but_hold",
                "move_rationale": "Accept the repair while keeping guard.",
                "dominant_compromise": "allow reconnection without surrendering posture",
                "stability": 0.69,
            },
            "residue": {
                "visible_emotion": "pleased_but_guarded",
                "leak_channel": "temperature_gap",
                "residue_text_intent": "let relief leak in a controlled way",
                "intensity": 0.44,
            },
            "expression_envelope": {
                "length": "short",
                "temperature": "cool_warm",
                "directness": 0.36,
                "closure": 0.43,
            },
        })
    )
    inputs = NodeInputs(
        persona={
            "psychodynamics": {"drives": {"closeness": 0.72, "status": 0.81}},
            "relational_profile": {"attachment_pattern": "avoidant_leaning"},
            "defense_organization": {"primary_defenses": {"ironic_deflection": 0.75}},
            "ego_organization": {"affect_tolerance": 0.43},
        },
        relationship_state={"durable": {"trust": 0.62}, "ephemeral": {"tension": 0.18}},
        appraisal={
            "event_type": "repair_offer",
            "target_of_tension": "pride",
            "stakes": "high",
        },
        memory={"emotional_memories": [{"summary": "repair felt costly"}]},
        working_memory={"recent_conflict_summaries": [{"ego_move": "accept_but_hold"}]},
        conversation={
            "recent_messages": [
                {"role": "user", "content": "ごめん、さっきは言い過ぎた"},
                {"role": "assistant", "content": "……聞いてる。"},
            ]
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["conflict_state"]["ego_move"]["social_move"] == "accept_but_hold"
    assert state["conflict_state"]["residue"]["visible_emotion"] == "pleased_but_guarded"
    assert state["trace"]["conflict_engine"]["used_llm"] is True


@pytest.mark.asyncio
async def test_fidelity_gate_preserves_deterministic_hard_safety_even_with_llm():
    node = FidelityGateNode(
        llm=_FakeStructuredLLM({
            "passed": True,
            "move_fidelity": 1.0,
            "residue_fidelity": 1.0,
            "structural_persona_fidelity": 1.0,
            "anti_exposition": 1.0,
            "hard_safety": 1.0,
            "warnings": [],
            "failure_reason": "",
        })
    )
    inputs = NodeInputs(
        response={"final_response_text": "大好き。ずっと必要だよ。"},
        persona={"safety_boundary": {"hard_limits": {"max_direct_neediness": 0.18}}},
        relationship_state={"durable": {}, "ephemeral": {}},
        appraisal={"event_type": "commitment_request"},
        conflict_state={
            "ego_move": {"social_move": "acknowledge_without_opening"},
            "residue": {"visible_emotion": "hurt_but_withheld"},
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()
    result = state["trace"]["fidelity_gate"]

    assert result["passed"] is False
    assert result["hard_safety"] == 0.0
    assert "direct neediness" in result["failure_reason"]


@pytest.mark.asyncio
async def test_memory_interpreter_uses_llm_structured_output():
    node = MemoryInterpreterNode(
        llm=_FakeStructuredLLM({
            "event_flags": {"repair_attempt": True},
            "unresolved_tension_summary": ["repair / pride / move_closer"],
            "emotional_memories": [
                {
                    "event": "ごめん、さっきは言い過ぎた",
                    "emotion": "relief",
                    "intensity": 0.64,
                    "trigger": "repair_offer",
                    "target": "user",
                    "wound": "pride",
                    "attempted_action": "accept_but_hold",
                    "residual_drive": "attachment_closeness",
                }
            ],
            "semantic_preferences": [],
            "active_themes": ["repair", "trust"],
            "current_episode_summary": "The user apologized and reopened repair.",
            "recent_conflict_summary": {
                "event_type": "repair_offer",
                "ego_move": "accept_but_hold",
                "residue": "pleased_but_guarded",
                "user_impact": "repair window opened",
                "relationship_delta": "warming",
            },
            "rationale_short": "Repair should persist as an unresolved but warming thread.",
        })
    )
    inputs = NodeInputs(
        request={"user_message": "ごめん、さっきは言い過ぎた"},
        response={"final_response_text": "…そう。受け取る。"},
        conversation={
            "recent_messages": [
                {"role": "user", "content": "ごめん、さっきは言い過ぎた"},
                {"role": "assistant", "content": "……聞いてる。"},
            ]
        },
        persona={
            "relational_profile": {"attachment_pattern": "avoidant_leaning"},
        },
        relationship_state={"durable": {"trust": 0.62}, "ephemeral": {"tension": 0.18}},
        mood={"base_mood": "defensive"},
        memory={"emotional_memories": [{"summary": "repair felt costly"}]},
        working_memory={"active_themes": ["repair"]},
        appraisal={"event_type": "repair_offer", "target_of_tension": "pride"},
        conflict_state={
            "ego_move": {"social_move": "accept_but_hold"},
            "residue": {"visible_emotion": "pleased_but_guarded"},
        },
        drive_state={"top_drives": [{"name": "attachment_closeness", "value": 0.8, "target": "user"}]},
        _internal={},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["memory_interpretation"]["event_flags"]["repair_attempt"] is True
    assert state["memory_interpretation"]["active_themes"] == ["repair", "trust"]
    assert state["trace"]["memory_interpreter"]["used_llm"] is True
    assert state["_internal"]["event_flags"]["repair_attempt"] is True
