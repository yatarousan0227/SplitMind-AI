"""Tests for SessionBootstrapNode persistent-memory integration."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.memory.markdown_store import MarkdownMemoryStore
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode


@pytest.fixture
def memory_store(tmp_path):
    return MarkdownMemoryStore(tmp_path)


@pytest.mark.asyncio
async def test_bootstrap_loads_cards_and_episodes_from_markdown_store(memory_store):
    memory_store.commit_turn(
        user_id="test_user",
        persona_name="cold_attached_idol",
        relationship_state={
            "durable": {
                "trust": 0.8,
                "intimacy": 0.6,
                "distance": 0.2,
                "attachment_pull": 0.5,
                "relationship_stage": "warming",
                "commitment_readiness": 0.3,
                "repair_depth": 0.1,
                "unresolved_tension_summary": ["repair_offer / pride / move_closer"],
            },
            "ephemeral": {},
        },
        mood={"base_mood": "calm", "openness": 0.7},
        memory_interpretation={
            "active_themes": ["repair", "trust"],
            "current_episode_summary": "Previous chat about repair.",
            "emotional_memories": [{"intensity": 0.7, "session_id": "prev", "turn_number": 4}],
        },
        working_memory={"active_themes": ["repair"]},
    )
    memory_store.commit_session(
        user_id="test_user",
        persona_name="cold_attached_idol",
        session_id="prev-session",
        session_digest={
            "text": "Previous chat",
            "turn_count": 5,
            "dominant_mood": "calm",
            "key_events": ["repair_attempt"],
        },
        final_state={"relationship_state": {"durable": {"relationship_stage": "warming"}}, "mood": {"base_mood": "calm"}},
    )

    node = SessionBootstrapNode(
        persona_name="cold_attached_idol",
        memory_store=memory_store,
    )

    inputs = NodeInputs(
        request={
            "session_id": "new-session",
            "user_id": "test_user",
            "user_message": "hello",
            "message": "hello",
            "action": "chat",
        },
        _internal={"is_first_turn": True, "turn_count": 0},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["relationship_state"]["durable"]["trust"] == 0.8
    assert state["relationship_state"]["durable"]["relationship_stage"] == "warming"
    assert state["mood"]["base_mood"] == "calm"
    assert len(state["memory"]["session_digests"]) == 1
    assert len(state["memory"]["episodes"]) == 1
    assert state["_internal"]["session"]["persona_self_name"] == "Airi"


@pytest.mark.asyncio
async def test_bootstrap_without_store_uses_defaults():
    node = SessionBootstrapNode(persona_name="cold_attached_idol")

    inputs = NodeInputs(
        request={
            "session_id": "test",
            "user_message": "hello",
            "message": "hello",
            "action": "chat",
        },
        _internal={"is_first_turn": True, "turn_count": 0},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["relationship_state"]["durable"]["trust"] == 0.5
    assert state["relationship_state"]["durable"]["relationship_stage"] == "unfamiliar"
    assert state["memory"]["episodes"] == []


@pytest.mark.asyncio
async def test_bootstrap_with_empty_store(memory_store):
    node = SessionBootstrapNode(
        persona_name="cold_attached_idol",
        memory_store=memory_store,
    )

    inputs = NodeInputs(
        request={
            "session_id": "test",
            "user_id": "new_user",
            "user_message": "hello",
            "message": "hello",
            "action": "chat",
        },
        _internal={"is_first_turn": True, "turn_count": 0},
    )

    outputs = await node.execute(inputs)
    state = outputs.to_state_updates()

    assert state["relationship_state"]["durable"]["trust"] == 0.5
    assert state["memory"]["session_digests"] == []
