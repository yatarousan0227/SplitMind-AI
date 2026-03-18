"""Tests for Obsidian vault store."""

import pytest

from splitmind_ai.memory.vault_store import VaultStore


@pytest.fixture
def vault(tmp_path):
    """Create a VaultStore backed by a temp directory."""
    return VaultStore(tmp_path)


class TestRelationshipState:
    def test_save_and_load_durable_relationship_state(self, vault):
        relationship_state = {
            "durable": {
                "trust": 0.6,
                "intimacy": 0.4,
                "distance": 0.3,
                "attachment_pull": 0.35,
                "relationship_stage": "warming",
                "commitment_readiness": 0.24,
                "repair_depth": 0.11,
                "unresolved_tension_summary": ["repair_offer / pride / move_closer"],
            },
            "ephemeral": {
                "tension": 0.1,
            },
        }
        vault.commit_turn("test_user", relationship_state, {"emotional_memories": [], "semantic_preferences": []})
        loaded = vault.load_relationship_state("test_user")

        assert loaded is not None
        assert loaded["trust"] == 0.6
        assert loaded["relationship_stage"] == "warming"
        assert loaded["unresolved_tension_summary"] == ["repair_offer / pride / move_closer"]

    def test_load_nonexistent(self, vault):
        assert vault.load_relationship_state("nobody") is None


class TestSessionSummaries:
    def test_save_and_load(self, vault):
        vault.save_session_summary(
            user_id="u1",
            session_id="s1",
            summary="Brief chat about music",
            turn_count=5,
            dominant_mood="playful",
            key_events=["discussed music"],
        )
        vault.save_session_summary(
            user_id="u1",
            session_id="s2",
            summary="Tense conversation",
            turn_count=3,
            dominant_mood="irritated",
        )

        sessions = vault.load_recent_sessions("u1", limit=3)
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "s2"


class TestEmotionalMemories:
    def test_save_and_load(self, vault):
        vault.save_emotional_memory("u1", {
            "event": "User praised a third party",
            "emotion": "jealousy",
            "trigger": "provocation",
            "target": "user",
            "wound": "status",
            "attempted_action": "accept_but_hold",
            "action_tendency": "accept_but_hold",
            "interaction_outcome": "tension_increase",
            "residual_drive": "be_first_for_user",
            "intensity": 0.7,
            "context": "Competitive response",
        })

        memories = vault.load_emotional_memories("u1")
        assert len(memories) == 1
        assert memories[0]["emotion"] == "jealousy"
        assert memories[0]["trigger"] == "provocation"


class TestSemanticPreferences:
    def test_save_and_load(self, vault):
        vault.save_semantic_preference("u1", {
            "topic": "music",
            "preference": "Likes jazz",
            "confidence": 0.8,
            "evidence": "Talked about live shows",
        })

        prefs = vault.load_semantic_preferences("u1")
        assert len(prefs) == 1
        assert prefs[0]["topic"] == "music"


class TestBulkLoad:
    def test_load_memory_context(self, vault):
        vault.save_session_summary("u1", "s1", "Summary", 3, "calm")
        vault.save_emotional_memory("u1", {
            "event": "Test event", "emotion": "warmth", "intensity": 0.5
        })
        vault.save_semantic_preference("u1", {
            "topic": "food", "preference": "Likes sushi"
        })

        ctx = vault.load_memory_context("u1")
        assert len(ctx["session_summaries"]) == 1
        assert len(ctx["emotional_memories"]) == 1
        assert len(ctx["semantic_preferences"]) == 1


class TestMoodSnapshot:
    def test_save_and_load(self, vault):
        mood = {
            "base_mood": "withdrawn",
            "irritation": 0.3,
            "longing": 0.5,
            "protectiveness": 0.0,
            "fatigue": 0.1,
            "openness": 0.4,
            "turns_since_shift": 2,
        }
        vault.save_mood("u1", mood)
        loaded = vault.load_mood("u1")

        assert loaded is not None
        assert loaded["base_mood"] == "withdrawn"
        assert loaded["irritation"] == pytest.approx(0.3, abs=0.01)


class TestCommitTurn:
    def test_commit_persists_relationship_state(self, vault):
        relationship_state = {
            "durable": {
                "trust": 0.7,
                "intimacy": 0.5,
                "distance": 0.3,
                "attachment_pull": 0.4,
                "relationship_stage": "charged",
                "commitment_readiness": 0.42,
                "repair_depth": 0.16,
                "unresolved_tension_summary": [],
            },
            "ephemeral": {
                "tension": 0.2,
            },
        }
        candidates = {
            "emotional_memories": [
                {"event": "Test", "emotion": "joy", "intensity": 0.6}
            ],
            "semantic_preferences": [],
        }

        vault.commit_turn("u1", relationship_state, candidates)

        loaded_rel = vault.load_relationship_state("u1")
        assert loaded_rel is not None
        assert loaded_rel["trust"] == 0.7
        assert loaded_rel["relationship_stage"] == "charged"
        assert "tension" not in loaded_rel

        memories = vault.load_emotional_memories("u1")
        assert len(memories) == 1

    def test_commit_persists_mood(self, vault):
        relationship_state = {"durable": {"trust": 0.6}, "ephemeral": {"tension": 0.1}}
        mood = {"base_mood": "irritated", "irritation": 0.5, "turns_since_shift": 1}
        candidates = {"emotional_memories": [], "semantic_preferences": []}

        vault.commit_turn("u1", relationship_state, candidates, mood=mood)

        loaded_mood = vault.load_mood("u1")
        assert loaded_mood is not None
        assert loaded_mood["base_mood"] == "irritated"
