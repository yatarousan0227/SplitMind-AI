"""Tests for next-generation conflict-pipeline prompt building."""

from splitmind_ai.prompts.conflict_pipeline import (
    build_appraisal_prompt,
    build_conflict_engine_prompt,
    build_expression_realizer_prompt,
    build_fidelity_gate_prompt,
    build_memory_interpreter_prompt,
)


def _persona() -> dict:
    return {
        "psychodynamics": {
            "drives": {"closeness": 0.72, "status": 0.81},
            "threat_sensitivity": {"rejection": 0.84, "shame": 0.76},
            "superego_configuration": {"pride_rigidity": 0.71, "dependency_shame": 0.79},
        },
        "relational_profile": {
            "attachment_pattern": "avoidant_leaning",
            "default_role_frame": "selective_one_to_one",
        },
        "defense_organization": {
            "primary_defenses": {"ironic_deflection": 0.75},
        },
        "ego_organization": {
            "affect_tolerance": 0.43,
            "impulse_regulation": 0.67,
            "ambivalence_capacity": 0.72,
            "mentalization": 0.64,
            "self_observation": 0.59,
            "self_disclosure_tolerance": 0.22,
            "warmth_recovery_speed": 0.37,
        },
        "safety_boundary": {
            "hard_limits": {"max_direct_neediness": 0.18},
        },
    }


def _relationship_state() -> dict:
    return {
        "durable": {
            "trust": 0.64,
            "intimacy": 0.43,
            "distance": 0.39,
            "attachment_pull": 0.57,
            "relationship_stage": "warming",
            "commitment_readiness": 0.28,
            "repair_depth": 0.17,
            "unresolved_tension_summary": ["status wobble after apology"],
        },
        "ephemeral": {
            "tension": 0.41,
            "recent_relational_charge": 0.58,
            "escalation_allowed": False,
            "interaction_fragility": 0.22,
            "turn_local_repair_opening": 0.47,
        },
    }


def test_appraisal_prompt_structure():
    messages = build_appraisal_prompt(
        user_message="ごめん、さっきは言い過ぎた",
        persona=_persona(),
        relationship_state=_relationship_state(),
        working_memory={"recent_conflict_summaries": [{"ego_move": "accept_but_hold"}]},
        conversation={
            "recent_messages": [
                {"role": "user", "content": "こんにちは"},
                {"role": "assistant", "content": "……なに。"},
            ]
        },
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "stimulus appraisal" in messages[0]["content"]
    assert "voice" in messages[0]["content"]
    assert "psychodynamics" in messages[0]["content"]
    assert "tone_guardrails" not in messages[0]["content"]
    assert "ごめん、さっきは言い過ぎた" in messages[1]["content"]
    assert "Recent Conversation" in messages[1]["content"]
    assert "Persona Psychodynamics" in messages[1]["content"]
    assert "Persona Relational Profile" in messages[1]["content"]


def test_conflict_engine_prompt_structure():
    messages = build_conflict_engine_prompt(
        persona=_persona(),
        relationship_state=_relationship_state(),
        appraisal={
            "event_type": "repair_offer",
            "valence": "mixed",
            "target_of_tension": "pride",
            "stakes": "high",
        },
        memory={"emotional_memories": [{"summary": "repair felt costly"}]},
        working_memory={"recent_conflict_summaries": [{"residue": "pleased_but_guarded"}]},
        conversation={
            "recent_messages": [
                {"role": "user", "content": "ごめん"},
                {"role": "assistant", "content": "……聞いてる。"},
            ]
        },
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "conflict engine" in messages[0]["content"]
    assert "話し方の指定" in messages[0]["content"]
    assert "persona を話し方の指定として扱わない" in messages[0]["content"]
    assert "ConflictState" in messages[0]["content"]
    assert "Recent Conversation" in messages[1]["content"]
    assert "Persona Identity" not in messages[1]["content"]
    assert "Defense Organization" in messages[1]["content"]
    assert "Ego Organization" in messages[1]["content"]
    assert "Stimulus Appraisal" in messages[1]["content"]


def test_expression_realizer_prompt_structure():
    messages = build_expression_realizer_prompt(
        user_message="私のこと、まだ嫌いじゃない？",
        response_language="en",
        persona=_persona(),
        relationship_state=_relationship_state(),
        appraisal={
            "event_type": "reassurance",
            "valence": "mixed",
            "target_of_tension": "closeness",
            "stakes": "medium",
        },
        conflict_state={
            "ego_move": {"social_move": "allow_dependence_but_reframe"},
            "residue": {"visible_emotion": "warm_but_measured"},
            "expression_envelope": {"length": "short", "temperature": "warm", "directness": 0.45, "closure": 0.3},
        },
        conversation={
            "recent_messages": [
                {"role": "user", "content": "こんにちは"},
                {"role": "assistant", "content": "遅かったね。"},
            ]
        },
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "expression realizer" in messages[0]["content"]
    assert "English" in messages[0]["content"]
    assert "カウンセラー調にしない" in messages[0]["content"]
    assert "how to speak" not in messages[0]["content"]
    assert "Recent Conversation" in messages[1]["content"]
    assert "Persona Identity" not in messages[1]["content"]
    assert "Response Language\nEnglish" in messages[1]["content"]
    assert "Conflict State" in messages[1]["content"]


def test_fidelity_gate_prompt_structure():
    messages = build_fidelity_gate_prompt(
        response_text="うん、そこは受け取る。次はもう少しちゃんと言って。",
        persona=_persona(),
        relationship_state=_relationship_state(),
        appraisal={"event_type": "repair_offer"},
        conflict_state={
            "ego_move": {"social_move": "accept_but_hold"},
            "residue": {"visible_emotion": "pleased_but_guarded"},
        },
        conversation={
            "recent_messages": [
                {"role": "user", "content": "ごめん"},
                {"role": "assistant", "content": "……まあ、聞く。"},
            ]
        },
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "fidelity gate" in messages[0]["content"]
    assert "書き直しはしない" in messages[0]["content"]
    assert "prohibited expressions" in messages[0]["content"]
    assert "Realized Response" in messages[1]["content"]
    assert "Recent Conversation" in messages[1]["content"]
    assert "Persona Identity" not in messages[1]["content"]
    assert "Safety Boundary" in messages[1]["content"]


def test_memory_interpreter_prompt_structure():
    messages = build_memory_interpreter_prompt(
        request={"user_message": "ごめん、さっきは言い過ぎた"},
        response={"final_response_text": "…そう。受け取る。"},
        persona=_persona(),
        relationship_state=_relationship_state(),
        mood={"base_mood": "defensive"},
        memory={"emotional_memories": [{"summary": "repair felt costly"}]},
        working_memory={"recent_conflict_summaries": [{"residue": "pleased_but_guarded"}]},
        appraisal={"event_type": "repair_offer", "target_of_tension": "pride"},
        conflict_state={"ego_move": {"social_move": "accept_but_hold"}},
        drive_state={"top_drives": [{"name": "attachment_closeness", "value": 0.8}]},
        conversation={
            "recent_messages": [
                {"role": "user", "content": "ごめん"},
                {"role": "assistant", "content": "……聞いてる。"},
            ]
        },
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "memory interpreter" in messages[0]["content"]
    assert "event_flags" in messages[0]["content"]
    assert "Recent Conversation" in messages[1]["content"]
    assert "Persona Identity" not in messages[1]["content"]
    assert "Final Response" in messages[1]["content"]
    assert "Drive State" in messages[1]["content"]
