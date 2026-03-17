"""Tests for Obsidian vault store."""

import json

import pytest

from splitmind_ai.memory.vault_store import VaultStore


@pytest.fixture
def vault(tmp_path):
    """Create a VaultStore backed by a temp directory."""
    return VaultStore(tmp_path)


class TestRelationship:
    def test_save_and_load(self, vault):
        rel = {
            "trust": 0.6,
            "intimacy": 0.4,
            "distance": 0.3,
            "tension": 0.1,
            "attachment_pull": 0.35,
            "unresolved_tensions": [
                {"theme": "fear_of_replacement", "intensity": 0.5,
                 "source": "test", "created_at": "2026-01-01",
                 "last_reinforced_at": "2026-01-01"}
            ],
        }
        vault.save_relationship("test_user", rel)
        loaded = vault.load_relationship("test_user")

        assert loaded is not None
        assert loaded["trust"] == 0.6
        assert loaded["intimacy"] == 0.4
        assert len(loaded["unresolved_tensions"]) == 1
        assert loaded["unresolved_tensions"][0]["theme"] == "fear_of_replacement"

    def test_load_nonexistent(self, vault):
        assert vault.load_relationship("nobody") is None


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
        # s2 should be first (sorted by filename, newest first)
        assert sessions[0]["session_id"] == "s2"

    def test_load_empty(self, vault):
        assert vault.load_recent_sessions("nobody") == []


class TestEmotionalMemories:
    def test_save_and_load(self, vault):
        vault.save_emotional_memory("u1", {
            "event": "User praised a third party",
            "emotion": "jealousy",
            "trigger": "fear_of_replacement",
            "target": "user",
            "wound": "special_to_user",
            "blocked_action": "full_disclosure",
            "attempted_action": "tease",
            "action_tendency": "test_user",
            "interaction_outcome": "tension_increase",
            "residual_drive": "territorial_exclusivity",
            "intensity": 0.7,
            "context": "Competitive response",
        })

        memories = vault.load_emotional_memories("u1")
        assert len(memories) == 1
        assert memories[0]["emotion"] == "jealousy"
        assert memories[0]["trigger"] == "fear_of_replacement"
        assert memories[0]["target"] == "user"
        assert memories[0]["wound"] == "special_to_user"
        assert memories[0]["blocked_action"] == "full_disclosure"
        assert memories[0]["attempted_action"] == "tease"
        assert memories[0]["residual_drive"] == "territorial_exclusivity"
        assert "User praised" in memories[0]["event"]

    def test_load_empty(self, vault):
        assert vault.load_emotional_memories("nobody") == []


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
        assert "jazz" in prefs[0]["preference"].lower()
        assert prefs[0]["evidence"] == "Talked about live shows"


class TestBulkLoad:
    def test_load_memory_context(self, vault):
        # Save some data
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

    def test_load_empty_context(self, vault):
        ctx = vault.load_memory_context("nobody")
        assert ctx["session_summaries"] == []
        assert ctx["emotional_memories"] == []
        assert ctx["semantic_preferences"] == []


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
        assert loaded["turns_since_shift"] == 2

    def test_load_nonexistent(self, vault):
        assert vault.load_mood("nobody") is None

    def test_overwrite(self, vault):
        vault.save_mood("u1", {"base_mood": "calm", "irritation": 0.0, "turns_since_shift": 0})
        vault.save_mood("u1", {"base_mood": "irritated", "irritation": 0.4, "turns_since_shift": 1})
        loaded = vault.load_mood("u1")
        assert loaded["base_mood"] == "irritated"


class TestCommitTurn:
    def test_commit_persists_relationship(self, vault):
        rel = {"trust": 0.7, "intimacy": 0.5, "unresolved_tensions": []}
        candidates = {
            "emotional_memories": [
                {"event": "Test", "emotion": "joy", "intensity": 0.6}
            ],
            "semantic_preferences": [],
        }

        vault.commit_turn("u1", rel, candidates)

        loaded_rel = vault.load_relationship("u1")
        assert loaded_rel is not None
        assert loaded_rel["trust"] == 0.7

        memories = vault.load_emotional_memories("u1")
        assert len(memories) == 1

    def test_commit_persists_mood(self, vault):
        rel = {"trust": 0.6, "unresolved_tensions": []}
        mood = {"base_mood": "irritated", "irritation": 0.5, "turns_since_shift": 1}
        candidates = {"emotional_memories": [], "semantic_preferences": []}

        vault.commit_turn("u1", rel, candidates, mood=mood)

        loaded_mood = vault.load_mood("u1")
        assert loaded_mood is not None
        assert loaded_mood["base_mood"] == "irritated"

    def test_commit_without_mood(self, vault):
        rel = {"trust": 0.6, "unresolved_tensions": []}
        candidates = {"emotional_memories": [], "semantic_preferences": []}

        # mood=None (default) should not raise
        vault.commit_turn("u1", rel, candidates)
        assert vault.load_mood("u1") is None


class TestTargetedRetrieval:
    def test_retrieve_relevant_memories_filters_emotional_and_semantic(self, vault):
        vault.save_emotional_memory("u1", {
            "event": "User praised a third party",
            "emotion": "jealousy",
            "trigger": "fear_of_replacement",
            "target": "user",
            "wound": "special_to_user",
            "blocked_action": "full_disclosure",
            "residual_drive": "territorial_exclusivity",
            "intensity": 0.7,
        })
        vault.save_emotional_memory("u1", {
            "event": "User apologized after conflict",
            "emotion": "relief",
            "trigger": "repair_attempt",
            "wound": "shame_after_exposure",
            "intensity": 0.5,
        })
        vault.save_semantic_preference("u1", {
            "topic": "music",
            "preference": "Likes jazz",
            "episode_hint": "concert talk",
        })
        vault.save_semantic_preference("u1", {
            "topic": "food",
            "preference": "Likes sushi",
        })

        results = vault.retrieve_relevant_memories(
            "u1",
            trigger="fear_of_replacement",
            target="user",
            blocked_action="full_disclosure",
            topic="music",
        )

        assert len(results["emotional_memories"]) == 1
        assert results["emotional_memories"][0]["trigger"] == "fear_of_replacement"
        assert results["emotional_memories"][0]["target"] == "user"
        assert len(results["semantic_preferences"]) == 1
        assert results["semantic_preferences"][0]["topic"] == "music"
