"""Tests for SessionBootstrapNode vault integration."""

import pytest
from agent_contracts import NodeInputs

from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode


@pytest.fixture
def vault(tmp_path):
    return VaultStore(tmp_path)


@pytest.mark.asyncio
async def test_bootstrap_loads_from_vault(vault):
    """Bootstrap should load relationship and memory from vault."""
    # Pre-populate vault
    vault.save_relationship("test_user", {
        "trust": 0.8,
        "intimacy": 0.6,
        "distance": 0.2,
        "tension": 0.1,
        "attachment_pull": 0.5,
        "unresolved_tensions": [
            {"theme": "fear_of_replacement", "intensity": 0.4,
             "source": "test", "created_at": "2026-01-01",
             "last_reinforced_at": "2026-01-01"}
        ],
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

    # Relationship loaded from vault
    assert state["relationship"]["trust"] == 0.8
    assert state["relationship"]["intimacy"] == 0.6
    assert len(state["relationship"]["unresolved_tensions"]) == 1

    # Memory loaded from vault
    assert len(state["memory"]["session_summaries"]) == 1
    assert len(state["memory"]["emotional_memories"]) == 1


@pytest.mark.asyncio
async def test_bootstrap_without_vault():
    """Bootstrap should work with defaults when no vault is provided."""
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

    # Should use defaults
    assert state["relationship"]["trust"] == 0.5
    assert state["memory"]["session_summaries"] == []


@pytest.mark.asyncio
async def test_bootstrap_with_empty_vault(vault):
    """Bootstrap should handle an empty vault gracefully."""
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

    # Should fall back to defaults
    assert state["relationship"]["trust"] == 0.5
    assert state["memory"]["session_summaries"] == []
