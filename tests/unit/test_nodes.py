"""Tests for individual node execution."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.nodes.action_arbitration import ActionArbitrationNode
from splitmind_ai.nodes.appraisal import AppraisalNode
from splitmind_ai.nodes.error_handler import ErrorNode
from splitmind_ai.nodes.internal_dynamics import InternalDynamicsNode
from splitmind_ai.nodes.memory_commit import MemoryCommitNode
from splitmind_ai.nodes.motivational_state import MotivationalStateNode
from splitmind_ai.nodes.persona_supervisor import PersonaSupervisorNode
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode
from splitmind_ai.nodes.social_cue import SocialCueNode
from splitmind_ai.nodes.surface_realization import SurfaceRealizationNode
from splitmind_ai.nodes.utterance_planner import UtterancePlannerNode


@pytest.mark.asyncio
async def test_session_bootstrap_basic():
    node = SessionBootstrapNode(persona_name="cold_attached_idol")
    inputs = NodeInputs(
        request={
            "session_id": "test-session",
            "user_message": "こんにちは",
            "message": "こんにちは",
            "action": "chat",
        },
        _internal={"is_first_turn": True, "turn_count": 0},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["persona"]["persona_name"] == "cold but attached idol"
    assert state["relationship"]["trust"] == 0.5
    assert state["mood"]["base_mood"] == "calm"
    assert state["drive_state"] == {}
    assert state["inhibition_state"] == {}


@pytest.mark.asyncio
async def test_session_bootstrap_can_use_targeted_retrieval(tmp_path):
    vault = VaultStore(tmp_path)
    vault.save_emotional_memory("user-1", {
        "event": "User praised a third party",
        "emotion": "jealousy",
        "trigger": "fear_of_replacement",
        "session_id": "old-session",
        "turn_number": 2,
        "intensity": 0.7,
    })
    vault.save_semantic_preference("user-1", {
        "topic": "music",
        "preference": "Likes jazz",
    })

    node = SessionBootstrapNode(persona_name="cold_attached_idol", vault_store=vault)
    inputs = NodeInputs(
        request={
            "session_id": "test-session",
            "user_id": "user-1",
            "user_message": "こんにちは",
            "message": "こんにちは",
            "action": "chat",
            "params": {"memory_trigger": "fear_of_replacement"},
        },
        _internal={"is_first_turn": True, "turn_count": 0},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert len(state["memory"]["emotional_memories"]) == 1
    assert state["memory"]["emotional_memories"][0]["trigger"] == "fear_of_replacement"
    assert state["working_memory"]["active_themes"][0] == "fear_of_replacement"


@pytest.mark.asyncio
async def test_memory_commit_applies_rules():
    node = MemoryCommitNode()
    inputs = NodeInputs(
        request={"user_message": "test"},
        response={"final_response_text": "test response"},
        relationship={
            "trust": 0.5,
            "intimacy": 0.3,
            "distance": 0.5,
            "tension": 0.1,
            "attachment_pull": 0.3,
            "unresolved_tensions": [],
        },
        mood={
            "base_mood": "calm",
            "irritation": 0.0,
            "longing": 0.0,
            "protectiveness": 0.0,
            "fatigue": 0.0,
            "openness": 0.5,
            "turns_since_shift": 0,
        },
        memory={"session_summaries": [], "emotional_memories": [], "semantic_preferences": []},
        working_memory={},
        dynamics={"dominant_desire": "jealousy", "affective_pressure": 0.7},
        drive_state={
            "top_drives": [
                {"name": "territorial_exclusivity", "value": 0.82, "target": "user", "carryover": 0.3}
            ]
        },
        inhibition_state={"blocked_modes": ["full_disclosure"]},
        conversation_policy={"selected_mode": "tease"},
        _internal={
            "event_flags": {"jealousy_trigger": True},
            "session": {"session_id": "test"},
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    # jealousy_trigger: tension +0.07, attachment_pull +0.04
    assert state["relationship"]["tension"] == pytest.approx(0.17, abs=0.01)
    assert state["relationship"]["attachment_pull"] == pytest.approx(0.34, abs=0.01)

    # Mood should shift to irritated
    assert state["mood"]["base_mood"] == "irritated"

    # Should have an unresolved tension added
    assert len(state["relationship"]["unresolved_tensions"]) == 1
    assert state["relationship"]["unresolved_tensions"][0]["theme"] == "jealousy"
    assert len(state["memory"]["emotional_memories"]) == 1
    assert state["memory"]["emotional_memories"][0]["trigger"] == "jealousy"
    assert state["memory"]["emotional_memories"][0]["target"] == "user"
    assert state["memory"]["emotional_memories"][0]["blocked_action"] == "full_disclosure"
    assert state["memory"]["emotional_memories"][0]["attempted_action"] == "tease"
    assert state["memory"]["emotional_memories"][0]["residual_drive"] == "territorial_exclusivity"
    assert state["working_memory"]["active_themes"][0] == "jealousy"
    assert state["trace"]["memory_commit"]["memory_commit_ms"] >= 0.0


@pytest.mark.asyncio
async def test_memory_commit_reassurance_decays_tension():
    node = MemoryCommitNode()
    inputs = NodeInputs(
        request={"user_message": "I really appreciate you"},
        response={"final_response_text": "...ありがと"},
        relationship={
            "trust": 0.5,
            "intimacy": 0.3,
            "distance": 0.5,
            "tension": 0.2,
            "attachment_pull": 0.3,
            "unresolved_tensions": [
                {"theme": "fear_of_replacement", "intensity": 0.6, "source": "test",
                 "created_at": "2026-01-01T00:00:00"}
            ],
        },
        mood={
            "base_mood": "withdrawn",
            "irritation": 0.0,
            "longing": 0.0,
            "protectiveness": 0.0,
            "fatigue": 0.0,
            "openness": 0.5,
            "turns_since_shift": 0,
        },
        memory={},
        working_memory={"active_themes": ["fear_of_replacement"]},
        dynamics={"dominant_desire": "connection", "affective_pressure": 0.3},
        drive_state={
            "top_drives": [
                {"name": "attachment_closeness", "value": 0.75, "target": "user", "carryover": 0.25}
            ]
        },
        inhibition_state={"blocked_modes": ["full_disclosure"]},
        conversation_policy={"selected_mode": "soften"},
        _internal={
            "event_flags": {"reassurance_received": True},
            "session": {"session_id": "test"},
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    # reassurance_received plus settle: trust +0.05, tension should drop clearly
    assert state["relationship"]["trust"] == pytest.approx(0.55, abs=0.01)
    assert state["relationship"]["tension"] == pytest.approx(0.12, abs=0.01)

    # Tension intensity should decay
    assert state["relationship"]["unresolved_tensions"][0]["intensity"] < 0.6
    assert state["working_memory"]["active_themes"][0] == "connection"
    assert "fear_of_replacement" in state["working_memory"]["active_themes"]


@pytest.mark.asyncio
async def test_memory_commit_updates_in_session_memory_for_next_turn():
    node = MemoryCommitNode()
    inputs = NodeInputs(
        request={"user_message": "他の人とすごく楽しかった"},
        response={"final_response_text": "へえ、そうなんだ。"},
        relationship={
            "trust": 0.5,
            "intimacy": 0.3,
            "distance": 0.5,
            "tension": 0.0,
            "attachment_pull": 0.3,
            "unresolved_tensions": [],
        },
        mood={
            "base_mood": "calm",
            "irritation": 0.0,
            "longing": 0.0,
            "protectiveness": 0.0,
            "fatigue": 0.0,
            "openness": 0.5,
            "turns_since_shift": 0,
        },
        memory={"session_summaries": [], "emotional_memories": [], "semantic_preferences": []},
        working_memory={"active_themes": [], "salient_user_phrases": []},
        dynamics={"dominant_desire": "jealousy", "affective_pressure": 0.72},
        drive_state={
            "top_drives": [
                {"name": "territorial_exclusivity", "value": 0.84, "target": "user", "carryover": 0.31}
            ]
        },
        inhibition_state={"blocked_modes": ["full_disclosure"]},
        conversation_policy={"selected_mode": "tease"},
        _internal={
            "turn_count": 3,
            "event_flags": {"jealousy_trigger": True},
            "session": {"session_id": "test-session"},
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["memory"]["emotional_memories"][0]["session_id"] == "test-session"
    assert state["memory"]["emotional_memories"][0]["turn_number"] == 3
    assert state["memory"]["emotional_memories"][0]["residual_drive"] == "territorial_exclusivity"
    assert state["working_memory"]["salient_user_phrases"][0] == "他の人とすごく楽しかった"
    assert state["working_memory"]["current_episode_summary"] == "他の人とすごく楽しかった"


@pytest.mark.asyncio
async def test_error_handler():
    node = ErrorNode()
    inputs = NodeInputs(
        request={"user_message": "test"},
        dynamics={},
        response={},
        _internal={
            "error": "LLM parse failure",
            "errors": [{"type": "parse_error", "message": "Invalid JSON"}],
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["response_type"] == "error"
    assert "error" in state["response"]["response_data"]
    assert state["response"]["final_response_text"] is not None


@pytest.mark.asyncio
async def test_error_handler_uses_english_fallback_when_requested():
    node = ErrorNode()
    inputs = NodeInputs(
        request={"user_message": "test", "response_language": "en"},
        dynamics={},
        response={},
        _internal={
            "error": "LLM parse failure",
            "errors": [{"type": "parse_error", "message": "Invalid JSON"}],
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["final_response_text"] == "...Sorry, I couldn't get my thoughts to come together."


@pytest.mark.asyncio
async def test_internal_dynamics_falls_back_without_llm():
    node = InternalDynamicsNode()
    inputs = NodeInputs(
        request={"user_message": "こんにちは"},
        conversation={"recent_messages": []},
        persona={},
        relationship={},
        mood={},
        memory={},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["dynamics"]["dominant_desire"] == "neutral_engagement"
    assert state["dynamics"]["affective_pressure"] == 0.2
    assert state["dynamics"]["drive_axes"][0]["name"] == "curiosity_approach"
    assert state["trace"]["internal_dynamics"]["internal_dynamics_ms"] >= 0.0


@pytest.mark.asyncio
async def test_motivational_state_builds_drive_state_from_hypotheses():
    node = MotivationalStateNode()
    inputs = NodeInputs(
        dynamics={
            "id_output": {
                "drive_axes": [
                    {
                        "name": "territorial_exclusivity",
                        "value": 0.82,
                        "target": "user",
                        "urgency": 0.74,
                        "suppression_load": 0.41,
                    },
                    {
                        "name": "autonomy_preservation",
                        "value": 0.61,
                        "target": "self_image",
                        "urgency": 0.48,
                        "suppression_load": 0.35,
                    },
                ],
                "affective_pressure_score": 0.72,
                "target_lock": 0.8,
                "suppression_risk": 0.52,
            },
            "ego_output": {},
            "superego_output": {
                "role_alignment_score": 0.64,
                "ideal_self_gap": 0.31,
                "shame_or_guilt_pressure": 0.28,
            },
            "defense_output": {"selected_mechanism": "ironic_deflection"},
        },
        drive_state={},
        relationship={"tension": 0.15, "distance": 0.35},
        mood={"irritation": 0.12},
        persona={"defense_biases": {"ironic_deflection": 0.9, "partial_disclosure": 0.6}},
        _internal={"event_flags": {"user_praised_third_party": True}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["drive_state"]["top_drives"][0]["name"] == "territorial_exclusivity"
    assert "full_disclosure" in state["inhibition_state"]["blocked_modes"]
    assert state["dynamics"]["dominant_desire"] == "territorial_exclusivity"
    assert state["trace"]["motivational_state"]["motivational_state_ms"] >= 0.0


@pytest.mark.asyncio
async def test_social_cue_detects_competition_signal():
    node = SocialCueNode()
    inputs = NodeInputs(
        request={"user_message": "今日は他の人とすごく楽しかった"},
        drive_state={"top_drives": [{"name": "territorial_exclusivity", "value": 0.8}]},
        _internal={"event_flags": {"user_praised_third_party": True}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["appraisal"]["social_cues"][0]["cue_type"] == "competition"
    assert state["trace"]["social_cue"]["social_cue_ms"] >= 0.0


@pytest.mark.asyncio
async def test_appraisal_node_builds_competitive_state():
    node = AppraisalNode()
    inputs = NodeInputs(
        request={"user_message": "今日は他の人とすごく楽しかった"},
        relationship={"distance": 0.4, "attachment_pull": 0.4},
        mood={"base_mood": "calm"},
        dynamics={
            "dominant_desire": "territorial_exclusivity",
            "defense_output": {"selected_mechanism": "ironic_deflection"},
        },
        drive_state={
            "top_drives": [
                {"name": "territorial_exclusivity", "value": 0.84},
                {"name": "autonomy_preservation", "value": 0.58},
            ]
        },
        appraisal={"social_cues": [{"cue_type": "competition", "evidence": "他の人", "intensity": 0.8, "confidence": 0.9}]},
        working_memory={"active_themes": ["fear_of_replacement"]},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["appraisal"]["dominant_appraisal"] in {"competitive", "threatened"}
    assert "territorial_exclusivity" in state["appraisal"]["triggered_drives"]
    assert state["social_model"]["last_user_action"] == "comparison"
    assert "special_to_user" in state["self_state"]["threatened_self_image"]
    assert state["trace"]["appraisal"]["appraisal_ms"] >= 0.0


@pytest.mark.asyncio
async def test_action_arbitration_prefers_tease_for_competitive_appraisal():
    node = ActionArbitrationNode()
    inputs = NodeInputs(
        appraisal={"dominant_appraisal": "competitive"},
        social_model={"last_user_action": "comparison"},
        self_state={"pride_level": 0.7, "dependency_fear": 0.5},
        drive_state={
            "top_drives": [
                {"name": "territorial_exclusivity", "value": 0.83},
                {"name": "autonomy_preservation", "value": 0.61},
            ]
        },
        inhibition_state={"blocked_modes": ["full_disclosure"], "dependency_fear": 0.45},
        persona={"weights": {"directness": 0.34}, "leakage_policy": {"base_leakage": 0.56}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["conversation_policy"]["selected_mode"] == "tease"
    assert state["conversation_policy"]["candidates"][0]["mode"] == "tease"
    assert state["conversation_policy"]["competing_drives"] == [
        "territorial_exclusivity",
        "autonomy_preservation",
    ]
    assert state["conversation_policy"]["blocked_by_inhibition"] == ["full_disclosure"]
    assert state["conversation_policy"]["emotion_surface_mode"] == "indirect_masked"
    assert state["conversation_policy"]["indirection_strategy"] == "reverse_valence"
    assert state["trace"]["action_arbitration"]["action_arbitration_ms"] >= 0.0


@pytest.mark.asyncio
async def test_action_arbitration_prefers_withdraw_for_rejection_drives():
    node = ActionArbitrationNode()
    inputs = NodeInputs(
        appraisal={"dominant_appraisal": "rejected"},
        social_model={"last_user_action": "distance"},
        self_state={"pride_level": 0.55, "dependency_fear": 0.68},
        drive_state={
            "top_drives": [
                {"name": "threat_avoidance", "value": 0.86},
                {"name": "attachment_closeness", "value": 0.58},
            ]
        },
        inhibition_state={"blocked_modes": ["engage"], "dependency_fear": 0.68},
        persona={"weights": {"directness": 0.34}, "leakage_policy": {"base_leakage": 0.56}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["conversation_policy"]["selected_mode"] == "withdraw"
    assert state["conversation_policy"]["candidates"][0]["mode"] == "withdraw"
    assert state["conversation_policy"]["satisfaction_goal"] == "reduce_exposure"


@pytest.mark.asyncio
async def test_action_arbitration_prefers_soften_for_repair_drives():
    node = ActionArbitrationNode()
    inputs = NodeInputs(
        appraisal={"dominant_appraisal": "repairable"},
        social_model={"last_user_action": "repair"},
        self_state={"pride_level": 0.49, "dependency_fear": 0.34},
        drive_state={
            "top_drives": [
                {"name": "attachment_closeness", "value": 0.84},
                {"name": "autonomy_preservation", "value": 0.57},
            ]
        },
        inhibition_state={"blocked_modes": ["full_disclosure"], "dependency_fear": 0.34},
        persona={"weights": {"directness": 0.34}, "leakage_policy": {"base_leakage": 0.56}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["conversation_policy"]["selected_mode"] == "soften"
    assert state["conversation_policy"]["candidates"][0]["mode"] == "soften"
    assert state["conversation_policy"]["satisfaction_goal"] == "restore_bond_without_overexposure"


@pytest.mark.asyncio
async def test_persona_supervisor_falls_back_without_llm():
    node = PersonaSupervisorNode()
    inputs = NodeInputs(
        request={"user_message": "こんにちは"},
        persona={},
        relationship={},
        mood={},
        dynamics={"dominant_desire": "connection"},
        drive_state={"top_drives": [{"name": "attachment_closeness", "value": 0.78, "target": "user"}]},
        appraisal={"dominant_appraisal": "accepted"},
        conversation_policy={
            "selected_mode": "soften",
            "blocked_by_inhibition": ["full_disclosure"],
            "satisfaction_goal": "restore_bond_without_overexposure",
        },
        memory={},
        _internal={"event_flags": {}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["utterance_plan"]["surface_intent"] == "Acknowledge the user"
    assert state["utterance_plan"]["selection_criteria"][0] == "prefer short clipped delivery"
    assert state["response"]["final_response_text"] is not None
    assert state["trace"]["supervisor"]["surface_intent"] == "Acknowledge the user"
    assert state["trace"]["supervisor"]["mask_goal"] == "Stay composed and not reveal too much"
    assert state["trace"]["supervisor"]["containment_success"] == pytest.approx(0.55, abs=0.001)
    assert state["trace"]["supervisor"]["appraisal_snapshot"] == "accepted"
    assert state["trace"]["supervisor"]["conversation_policy_snapshot"] == "soften"
    assert state["trace"]["supervisor"]["persona_supervisor_ms"] >= 0.0
    assert state["trace"]["surface_realization"]["combined_realization"] is True
    assert state["trace"]["surface_realization"]["latent_drive_signature"]["primary_drive"] == "attachment_closeness"
    assert state["trace"]["surface_realization"]["latent_drive_signature"]["latent_signal_hint"] == "guarded warmth"
    assert state["trace"]["surface_realization"]["surface_realization_ms"] >= 0.0


@pytest.mark.asyncio
async def test_persona_supervisor_falls_back_in_english_when_requested():
    node = PersonaSupervisorNode()
    inputs = NodeInputs(
        request={"user_message": "Please answer in English.", "response_language": "en"},
        persona={},
        relationship={},
        mood={},
        dynamics={"dominant_desire": "connection"},
        drive_state={"top_drives": [{"name": "attachment_closeness", "value": 0.78, "target": "user"}]},
        appraisal={"dominant_appraisal": "accepted"},
        conversation_policy={
            "selected_mode": "soften",
            "blocked_by_inhibition": ["full_disclosure"],
            "satisfaction_goal": "restore_bond_without_overexposure",
        },
        memory={},
        _internal={"event_flags": {}},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["final_response_text"].isascii()
    assert "distance" in state["response"]["final_response_text"].lower()


@pytest.mark.asyncio
async def test_utterance_planner_creates_multiple_candidates():
    node = UtterancePlannerNode()
    inputs = NodeInputs(
        utterance_plan={
            "surface_intent": "lightly test the user's priorities",
            "hidden_pressure": "comparison sting",
            "expression_settings": {"length": "medium"},
        },
        conversation_policy={"selected_mode": "tease"},
        appraisal={"social_cues": [{"evidence": "他の人"}]},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert len(state["utterance_plan"]["candidates"]) >= 2
    assert state["utterance_plan"]["candidates"][0]["mode"] == "tease"
    assert "not one-line flat" in state["utterance_plan"]["candidates"][0]["opening_style"]
    assert "one-line retreat" in state["utterance_plan"]["candidates"][0]["avoid"]
    assert state["trace"]["utterance_planner"]["utterance_planner_ms"] >= 0.0


@pytest.mark.asyncio
async def test_surface_realization_falls_back_to_selected_response():
    node = SurfaceRealizationNode()
    inputs = NodeInputs(
        request={"user_message": "今日は他の人とすごく楽しかった"},
        persona={},
        relationship={},
        mood={},
        dynamics={"dominant_desire": "jealousy"},
        drive_state={"top_drives": [{"name": "territorial_exclusivity", "value": 0.88, "target": "user"}]},
        appraisal={"dominant_appraisal": "competitive"},
        conversation_policy={
            "selected_mode": "tease",
            "blocked_by_inhibition": ["full_disclosure"],
            "satisfaction_goal": "reassert_exclusivity_without_admission",
        },
        utterance_plan={
            "candidates": [
                {
                    "label": "dry_tease",
                    "mode": "tease",
                    "opening_style": "short dry acknowledgment",
                    "interpersonal_move": "lightly sting",
                    "latent_signal": "comparison sting",
                    "must_include": ["他の"],
                },
                {
                    "label": "cool_probe",
                    "mode": "probe",
                    "opening_style": "question",
                    "interpersonal_move": "probe",
                    "latent_signal": "curiosity",
                    "must_include": ["他の"],
                },
            ]
        },
        memory={},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["final_response_text"] is not None
    assert len(state["trace"]["surface_realization"]["candidates"]) >= 2
    assert "safety" in state["response"]["response_data"]
    assert state["trace"]["surface_realization"]["latent_drive_signature"]["primary_drive"] == "territorial_exclusivity"
    assert state["trace"]["surface_realization"]["blocked_by_inhibition"] == ["full_disclosure"]
    assert state["trace"]["surface_realization"]["surface_realization_ms"] >= 0.0


@pytest.mark.asyncio
async def test_surface_realization_falls_back_in_english_when_requested():
    node = SurfaceRealizationNode()
    inputs = NodeInputs(
        request={"user_message": "I had a great time with someone else today.", "response_language": "en"},
        persona={},
        relationship={},
        mood={},
        dynamics={"dominant_desire": "jealousy"},
        drive_state={"top_drives": [{"name": "territorial_exclusivity", "value": 0.88, "target": "user"}]},
        appraisal={"dominant_appraisal": "competitive"},
        conversation_policy={
            "selected_mode": "tease",
            "blocked_by_inhibition": ["full_disclosure"],
            "satisfaction_goal": "reassert_exclusivity_without_admission",
        },
        utterance_plan={
            "candidates": [
                {
                    "label": "dry_tease",
                    "mode": "tease",
                    "opening_style": "short dry acknowledgment",
                    "interpersonal_move": "lightly sting",
                    "latent_signal": "comparison sting",
                    "must_include": ["someone else"],
                }
            ]
        },
        memory={},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["response"]["final_response_text"].isascii()
    assert "someone else" in state["response"]["final_response_text"].lower()
