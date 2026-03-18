"""Targeted tests for phase-5 prompt-backed realization nodes."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.nodes.appraisal import AppraisalNode
from splitmind_ai.nodes.conflict_engine import ConflictEngineNode
from splitmind_ai.nodes.expression_realizer import ExpressionRealizerNode, _realize_text
from splitmind_ai.nodes.fidelity_gate import FidelityGateNode
from splitmind_ai.nodes.memory_interpreter import MemoryInterpreterNode
from splitmind_ai.nodes.turn_shaping_policy import TurnShapingPolicyNode
from splitmind_ai.personas.loader import load_persona


class _FakeStructuredLLM:
    def __init__(self, payload: dict | None = None, *, payloads_by_schema: dict[str, dict] | None = None):
        self._payload = payload
        self._payloads_by_schema = payloads_by_schema or {}
        self._schema = None

    def with_structured_output(self, schema, method: str | None = None):
        self._schema = schema
        return self

    async def ainvoke(self, messages):
        payload = self._payloads_by_schema.get(self._schema.__name__, self._payload)
        if payload is None:
            raise AssertionError(f"Missing fake payload for schema {self._schema.__name__}")
        return self._schema.model_validate(payload)


@pytest.mark.asyncio
async def test_appraisal_uses_llm_structured_output_with_conversation_context():
    node = AppraisalNode(
        llm=_FakeStructuredLLM(payloads_by_schema={
            "RelationalCueParse": {
                "cues": [
                    {
                        "label": "timing_pushback",
                        "evidence": "今は話さないの？",
                        "intensity": 0.72,
                        "confidence": 0.81,
                    }
                ],
                "event_mix": {
                    "primary_event": "boundary_test",
                    "secondary_events": ["ambiguity"],
                    "comparison_frame": "none",
                    "repair_signal_strength": 0.0,
                    "priority_signal_strength": 0.0,
                    "distance_signal_strength": 0.0,
                },
                "speaker_intent": {
                    "user_distance_request": False,
                    "user_repair_bid": False,
                    "user_comparison_target": "",
                    "user_commitment_signal": False,
                    "user_is_describing_own_state": False,
                },
                "perspective_guard": {
                    "preserve_user_as_subject": False,
                    "disallow_assistant_self_distancing": False,
                    "rationale": "",
                },
                "target_hint": "control",
                "valence_hint": "mixed",
                "stakes_hint": "medium",
                "user_intent_guess": "seek_immediate_contact",
                "active_themes": ["contact", "timing"],
            },
            "StimulusAppraisal": {
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
                "event_mix": {
                    "primary_event": "boundary_test",
                    "secondary_events": ["ambiguity"],
                    "comparison_frame": "none",
                    "repair_signal_strength": 0.0,
                    "priority_signal_strength": 0.0,
                    "distance_signal_strength": 0.0,
                },
            },
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
    assert state["appraisal"]["event_mix"]["primary_event"] == "boundary_test"
    assert state["trace"]["appraisal"]["relational_cue_parse"]["target_hint"] == "control"
    assert state["trace"]["appraisal"]["used_llm"] is True


@pytest.mark.asyncio
async def test_appraisal_carries_relational_cue_parse_for_third_party_comparison():
    node = AppraisalNode(
        llm=_FakeStructuredLLM(payloads_by_schema={
            "RelationalCueParse": {
                "cues": [
                    {
                        "label": "comparison_or_priority",
                        "evidence": "あの子ってすごく優しいよね、見習いたいな",
                        "intensity": 0.82,
                        "confidence": 0.8,
                    }
                ],
                "event_mix": {
                    "primary_event": "provocation",
                    "secondary_events": ["good_news"],
                    "comparison_frame": "third_party_comparison",
                    "repair_signal_strength": 0.0,
                    "priority_signal_strength": 0.61,
                    "distance_signal_strength": 0.0,
                },
                "speaker_intent": {
                    "user_distance_request": False,
                    "user_repair_bid": False,
                    "user_comparison_target": "third_party",
                    "user_commitment_signal": False,
                    "user_is_describing_own_state": False,
                },
                "perspective_guard": {
                    "preserve_user_as_subject": False,
                    "disallow_assistant_self_distancing": False,
                    "rationale": "",
                },
                "target_hint": "jealousy",
                "valence_hint": "mixed",
                "stakes_hint": "medium",
                "user_intent_guess": "test_comparison_reaction",
                "active_themes": ["fear_of_replacement", "comparison"],
            },
            "StimulusAppraisal": {
                "event_type": "provocation",
                "valence": "mixed",
                "target_of_tension": "jealousy",
                "stakes": "medium",
                "confidence": 0.74,
                "cues": [],
                "summary_short": "User introduces a third-party comparison frame.",
                "user_intent_guess": "",
                "active_themes": ["comparison"],
            },
        })
    )
    inputs = NodeInputs(
        request={"user_message": "あの子ってすごく優しいよね、見習いたいな"},
        persona={
            "psychodynamics": {"drives": {"closeness": 0.8}},
            "relational_profile": {"attachment_pattern": "avoidant_leaning"},
        },
        relationship_state={"durable": {"trust": 0.52}, "ephemeral": {"tension": 0.18}},
        working_memory={"active_themes": ["fear_of_replacement"]},
        conversation={"recent_messages": []},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["appraisal"]["event_type"] == "provocation"
    assert state["appraisal"]["target_of_tension"] == "jealousy"
    assert state["appraisal"]["event_mix"]["comparison_frame"] == "third_party_comparison"
    assert state["appraisal"]["speaker_intent"]["user_comparison_target"] == "third_party"
    assert "fear_of_replacement" in state["appraisal"]["active_themes"]


@pytest.mark.asyncio
async def test_appraisal_preserves_user_distance_request_from_relational_cue_parse():
    node = AppraisalNode(
        llm=_FakeStructuredLLM(payloads_by_schema={
            "RelationalCueParse": {
                "cues": [
                    {
                        "label": "distancing",
                        "evidence": "あかんわ、離れないとダメな気がする",
                        "intensity": 0.93,
                        "confidence": 0.89,
                    }
                ],
                "event_mix": {
                    "primary_event": "distancing",
                    "secondary_events": ["ambiguity"],
                    "comparison_frame": "none",
                    "repair_signal_strength": 0.0,
                    "priority_signal_strength": 0.0,
                    "distance_signal_strength": 0.93,
                },
                "speaker_intent": {
                    "user_distance_request": True,
                    "user_repair_bid": False,
                    "user_comparison_target": "",
                    "user_commitment_signal": False,
                    "user_is_describing_own_state": True,
                },
                "perspective_guard": {
                    "preserve_user_as_subject": True,
                    "disallow_assistant_self_distancing": True,
                    "rationale": "user is describing their own need for distance",
                },
                "target_hint": "safety",
                "valence_hint": "negative",
                "stakes_hint": "high",
                "user_intent_guess": "create_distance",
                "active_themes": ["distance"],
            },
            "StimulusAppraisal": {
                "event_type": "distancing",
                "valence": "negative",
                "target_of_tension": "safety",
                "stakes": "high",
                "confidence": 0.51,
                "cues": [],
                "summary_short": "User expresses a need to pull away.",
                "user_intent_guess": "",
                "active_themes": [],
            },
        })
    )
    inputs = NodeInputs(
        request={"user_message": "あかんわ、離れないとダメな気がする"},
        persona={
            "psychodynamics": {"drives": {"closeness": 0.8}},
            "relational_profile": {"attachment_pattern": "avoidant_leaning"},
        },
        relationship_state={"durable": {"trust": 0.58}, "ephemeral": {"tension": 0.16}},
        working_memory={"active_themes": []},
        conversation={"recent_messages": []},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["appraisal"]["event_type"] == "distancing"
    assert state["appraisal"]["speaker_intent"]["user_distance_request"] is True
    assert state["appraisal"]["perspective_guard"]["disallow_assistant_self_distancing"] is True


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

    text = state["response"]["final_response_text"]
    assert text
    assert "Airi" not in text
    assert "Cold Attached Idol" not in text
    assert len([segment for segment in text.replace(".", "\n").splitlines() if segment.strip()]) >= 2
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

    assert state["conflict_state"]["ego_move"]["move_family"] == "repair_acceptance"
    assert state["conflict_state"]["ego_move"]["move_style"] == "accept_but_hold"
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


@pytest.mark.asyncio
async def test_turn_shaping_policy_separates_counterforce_for_same_repair_turn():
    personas = {
        name: load_persona(name).to_slice()["relational_policy"]
        for name in (
            "cold_attached_idol",
            "angelic_but_deliberate",
            "warm_guarded_companion",
            "irresistibly_sweet_center_heroine",
        )
    }
    node = TurnShapingPolicyNode()
    results = {}
    for name, relational_policy in personas.items():
        outputs = await node.execute(NodeInputs(
            relational_policy=relational_policy,
            relationship_state={
                "durable": {"trust": 0.48, "intimacy": 0.34, "attachment_pull": 0.44},
                "ephemeral": {"tension": 0.22, "turn_local_repair_opening": 0.28},
            },
            appraisal={
                "event_type": "affection_signal",
                "event_mix": {
                    "primary_event": "affection_signal",
                    "secondary_events": ["repair_offer"],
                    "comparison_frame": "none",
                    "repair_signal_strength": 0.74,
                    "priority_signal_strength": 0.58,
                    "distance_signal_strength": 0.0,
                },
                "speaker_intent": {"user_repair_bid": True, "user_commitment_signal": False},
                "relational_act_profile": {
                    "affection": 0.72,
                    "repair_bid": 0.78,
                    "reassurance": 0.66,
                    "commitment": 0.12,
                    "priority_restore": 0.58,
                    "comparison": 0.0,
                    "distancing": 0.0,
                },
            },
            conflict_state={
                "ego_move": {"move_family": "repair_acceptance", "move_style": "accept_but_hold"},
                "expression_envelope": {"closure": 0.42},
            },
            residue_state={"overall_load": 0.26},
        ))
        state = outputs.to_state_updates()
        results[name] = state["turn_shaping_policy"]["preserved_counterforce"]

    assert results["cold_attached_idol"] in {"sting", "distance"}
    assert results["angelic_but_deliberate"] == "status"
    assert results["warm_guarded_companion"] == "pace"
    assert results["irresistibly_sweet_center_heroine"] == "pace"


@pytest.mark.asyncio
async def test_turn_shaping_policy_projects_compatibility_policies():
    node = TurnShapingPolicyNode()
    outputs = await node.execute(NodeInputs(
        relational_policy=load_persona("irresistibly_sweet_center_heroine").to_slice()["relational_policy"],
        relationship_state={
            "durable": {"trust": 0.62, "intimacy": 0.48, "attachment_pull": 0.55},
            "ephemeral": {"tension": 0.08, "turn_local_repair_opening": 0.46},
        },
        appraisal={
            "event_type": "repair_offer",
            "event_mix": {"primary_event": "repair_offer", "secondary_events": ["affection_signal"], "comparison_frame": "none"},
            "speaker_intent": {"user_repair_bid": True},
            "relational_act_profile": {
                "affection": 0.74,
                "repair_bid": 0.82,
                "reassurance": 0.68,
                "commitment": 0.0,
                "priority_restore": 0.44,
                "comparison": 0.0,
                "distancing": 0.0,
            },
        },
        conflict_state={"ego_move": {"move_family": "repair_acceptance", "move_style": "affectionate_inclusion"}},
        residue_state={"overall_load": 0.12},
    ))
    state = outputs.to_state_updates()
    shaping = state["turn_shaping_policy"]

    assert shaping["forbidden_collapses"]["full_repair_reset"] is True
    assert shaping["required_surface_markers"]["pace_marker"] is True
    assert state["repair_policy"]["repair_mode"] in {"receptive", "integrative"}


def test_fallback_realizer_branches_on_counterforce():
    base_kwargs = {
        "response_language": "ja",
        "persona": {},
        "relationship_state": {"durable": {"trust": 0.52}},
        "appraisal": {"event_type": "repair_offer"},
        "conflict_state": {
            "ego_move": {"move_family": "repair_acceptance", "move_style": "accept_but_hold"},
            "residue": {"visible_emotion": "pleased_but_guarded"},
        },
        "repair_policy": {"repair_mode": "guarded"},
        "comparison_policy": {},
    }

    status_text = _realize_text(
        **base_kwargs,
        turn_shaping_policy={
            "primary_frame": "repair_acceptance",
            "secondary_frame": "affection_receipt",
            "preserved_counterforce": "status",
            "forbidden_collapses": {"full_repair_reset": True},
        },
    )
    sting_text = _realize_text(
        **base_kwargs,
        turn_shaping_policy={
            "primary_frame": "repair_acceptance",
            "secondary_frame": "affection_receipt",
            "preserved_counterforce": "sting",
            "forbidden_collapses": {"full_repair_reset": True},
        },
    )
    pace_text = _realize_text(
        **base_kwargs,
        turn_shaping_policy={
            "primary_frame": "repair_acceptance",
            "secondary_frame": "affection_receipt",
            "preserved_counterforce": "pace",
            "forbidden_collapses": {"full_repair_reset": True},
        },
    )
    distance_text = _realize_text(
        **base_kwargs,
        turn_shaping_policy={
            "primary_frame": "repair_acceptance",
            "secondary_frame": "affection_receipt",
            "preserved_counterforce": "distance",
            "forbidden_collapses": {"full_repair_reset": True},
        },
    )

    texts = [status_text, sting_text, pace_text, distance_text]
    assert all(text.endswith("。") for text in texts)
    assert len(set(texts)) == 4
    assert all(len([segment for segment in text.split("。") if segment.strip()]) >= 2 for text in texts)
