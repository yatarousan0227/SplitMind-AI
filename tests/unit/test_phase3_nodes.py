"""Targeted tests for phase-3 relationship persistence nodes."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.nodes.memory_commit import MemoryCommitNode
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode


@pytest.mark.asyncio
async def test_session_bootstrap_emits_relationship_state():
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

    assert state["persona"]["psychodynamics"]["drives"]["closeness"] == pytest.approx(0.72)
    assert state["relationship_state"]["durable"]["trust"] == 0.5
    assert state["relationship_state"]["durable"]["relationship_stage"] == "unfamiliar"
    assert state["relationship_state"]["ephemeral"]["tension"] == 0.0
    assert state["working_memory"]["recent_conflict_summaries"] == []


@pytest.mark.asyncio
async def test_memory_commit_updates_relationship_state_and_working_memory():
    node = MemoryCommitNode()
    inputs = NodeInputs(
        request={"user_message": "ごめん、さっきは言い過ぎた"},
        response={"final_response_text": "うん、そこは受け取る。"},
        relationship_state={
            "durable": {
                "trust": 0.5,
                "intimacy": 0.3,
                "distance": 0.5,
                "attachment_pull": 0.3,
                "relationship_stage": "warming",
                "commitment_readiness": 0.22,
                "repair_depth": 0.0,
                "unresolved_tension_summary": ["old tension"],
            },
            "ephemeral": {
                "tension": 0.18,
                "recent_relational_charge": 0.0,
                "escalation_allowed": False,
                "interaction_fragility": 0.0,
                "turn_local_repair_opening": 0.0,
            },
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
        memory={"session_summaries": [], "emotional_memories": [], "semantic_preferences": []},
        working_memory={"active_themes": [], "salient_user_phrases": [], "recent_conflict_summaries": []},
        appraisal={"event_type": "repair_offer", "target_of_tension": "pride"},
        conflict_state={
            "id_impulse": {"dominant_want": "move_closer", "intensity": 0.62, "target": "user"},
            "superego_pressure": {"pressure": 0.71},
            "ego_move": {"social_move": "accept_but_hold"},
            "residue": {"visible_emotion": "pleased_but_guarded", "intensity": 0.43},
        },
        drive_state={
            "top_drives": [
                {"name": "attachment_closeness", "value": 0.78, "target": "user", "carryover": 0.25}
            ]
        },
        memory_interpretation={
            "event_flags": {"repair_attempt": True},
            "unresolved_tension_summary": ["repair / pride / move_closer"],
            "emotional_memories": [
                {
                    "event": "ごめん、さっきは言い過ぎた",
                    "emotion": "relief",
                    "intensity": 0.64,
                    "trigger": "repair_offer",
                    "target": "user",
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
        },
        _internal={
            "event_flags": {"repair_attempt": True},
            "session": {"session_id": "test"},
            "turn_count": 1,
        },
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["relationship_state"]["durable"]["trust"] > 0.5
    assert state["relationship_state"]["durable"]["repair_depth"] > 0.0
    assert state["relationship_state"]["ephemeral"]["turn_local_repair_opening"] > 0.0
    assert len(state["memory"]["emotional_memories"]) == 1
    assert state["working_memory"]["active_themes"] == ["repair", "trust"]
    assert state["working_memory"]["current_episode_summary"] == "The user apologized and reopened repair."
    assert state["working_memory"]["recent_conflict_summaries"][0]["ego_move"] == "accept_but_hold"
    assert state["trace"]["memory_commit"]["used_memory_interpretation"] is True
    assert state["trace"]["memory_commit"]["memory_commit_ms"] >= 0.0
