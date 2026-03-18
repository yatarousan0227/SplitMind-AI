"""Tests for SessionBootstrapNode vault integration."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode


@pytest.fixture
def vault(tmp_path):
    return VaultStore(tmp_path)


@pytest.mark.asyncio
async def test_bootstrap_loads_durable_relationship_state_from_vault(vault):
    vault.save_relationship_state("test_user", {
        "trust": 0.8,
        "intimacy": 0.6,
        "distance": 0.2,
        "attachment_pull": 0.5,
        "relationship_stage": "warming",
        "commitment_readiness": 0.3,
        "repair_depth": 0.1,
        "unresolved_tension_summary": ["repair_offer / pride / move_closer"],
    })
    vault.save_session_summary("test_user", "prev-session", "Previous chat", 5, "calm")
    vault.save_emotional_memory("test_user", {
        "event": "Past event", "emotion": "joy", "intensity": 0.6
    })

    node = SessionBootstrapNode(
        persona_name="cold_attached_idol",
        vault_store=vault,
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
    assert state["relationship_state"]["ephemeral"]["tension"] == 0.0
    assert len(state["memory"]["session_summaries"]) == 1
    assert len(state["memory"]["emotional_memories"]) == 1


@pytest.mark.asyncio
async def test_bootstrap_without_vault_uses_defaults():
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
    assert state["memory"]["session_summaries"] == []


@pytest.mark.asyncio
async def test_bootstrap_with_empty_vault(vault):
    node = SessionBootstrapNode(
        persona_name="cold_attached_idol",
        vault_store=vault,
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
    assert state["memory"]["session_summaries"] == []
