"""Tests for the markdown-backed persistent memory store."""

import pytest

from splitmind_ai.memory.markdown_store import MarkdownMemoryStore


@pytest.fixture
def memory_store(tmp_path):
    return MarkdownMemoryStore(tmp_path)


def test_commit_turn_persists_relationship_and_psychological_cards(memory_store):
    memory_store.commit_turn(
        user_id="u1",
        persona_name="cold_attached_idol",
        relationship_state={
            "durable": {
                "trust": 0.7,
                "intimacy": 0.5,
                "distance": 0.3,
                "attachment_pull": 0.4,
                "relationship_stage": "charged",
                "commitment_readiness": 0.42,
                "repair_depth": 0.16,
                "unresolved_tension_summary": ["status wobble"],
            },
            "ephemeral": {"tension": 0.2},
        },
        mood={"base_mood": "irritated", "irritation": 0.5, "turns_since_shift": 1},
        memory_interpretation={
            "event_flags": {"jealousy_trigger": True},
            "active_themes": ["priority", "status wobble"],
            "unresolved_tension_summary": ["status wobble"],
            "current_episode_summary": "The user mentioned someone else and stirred status tension.",
            "recent_conflict_summary": {
                "event_type": "comparison",
                "ego_move": "stung_then_withhold",
                "residue": "irritation",
            },
            "emotional_memories": [
                {
                    "event": "comparison event",
                    "emotion": "irritation",
                    "intensity": 0.76,
                    "session_id": "s1",
                    "turn_number": 2,
                }
            ],
        },
        working_memory={"active_themes": ["priority"], "current_episode_summary": "comparison"},
    )

    context = memory_store.load_bootstrap_context(
        user_id="u1",
        persona_name="cold_attached_idol",
        query_context={"user_message": "priority"},
    )

    assert context["relationship_state"]["durable"]["trust"] == pytest.approx(0.7)
    assert context["mood"]["base_mood"] == "irritated"
    assert context["memory"]["psychological_card"]["current_relational_stance"] == "charged"
    assert len(context["memory"]["episodes"]) == 1


def test_bootstrap_context_is_scoped_by_user_and_persona(memory_store):
    for persona_name, trust in (("cold_attached_idol", 0.8), ("warm_guarded_companion", 0.3)):
        memory_store.commit_turn(
            user_id="alice",
            persona_name=persona_name,
            relationship_state={"durable": {"trust": trust, "relationship_stage": "warming"}, "ephemeral": {}},
            mood={"base_mood": "calm"},
            memory_interpretation={"current_episode_summary": f"episode for {persona_name}"},
            working_memory={},
        )

    cold = memory_store.load_bootstrap_context(
        user_id="alice",
        persona_name="cold_attached_idol",
        query_context={"user_message": "episode"},
    )
    warm = memory_store.load_bootstrap_context(
        user_id="alice",
        persona_name="warm_guarded_companion",
        query_context={"user_message": "episode"},
    )

    assert cold["relationship_state"]["durable"]["trust"] == pytest.approx(0.8)
    assert warm["relationship_state"]["durable"]["trust"] == pytest.approx(0.3)
    assert cold["memory"]["episodes"][0]["summary"] != warm["memory"]["episodes"][0]["summary"]


def test_bootstrap_retrieval_limits_episodes_to_four(memory_store):
    for index in range(6):
        memory_store.commit_turn(
            user_id="u1",
            persona_name="cold_attached_idol",
            relationship_state={"durable": {"trust": 0.5, "relationship_stage": "warming"}, "ephemeral": {}},
            mood={"base_mood": "calm"},
            memory_interpretation={
                "active_themes": ["music", f"theme-{index}"],
                "current_episode_summary": f"music episode {index}",
                "emotional_memories": [{"intensity": 0.2 + (index * 0.1)}],
            },
            working_memory={"active_themes": ["music"]},
        )

    context = memory_store.load_bootstrap_context(
        user_id="u1",
        persona_name="cold_attached_idol",
        query_context={"user_message": "music"},
    )

    assert len(context["memory"]["episodes"]) == 4


def test_compaction_keeps_episode_count_bounded(memory_store):
    for index in range(65):
        memory_store.commit_turn(
            user_id="u1",
            persona_name="cold_attached_idol",
            relationship_state={"durable": {"trust": 0.5, "relationship_stage": "warming"}, "ephemeral": {}},
            mood={"base_mood": "calm"},
            memory_interpretation={
                "active_themes": [f"theme-{index}"],
                "current_episode_summary": f"episode {index}",
                "emotional_memories": [{"intensity": 0.4}],
            },
            working_memory={"active_themes": [f"theme-{index}"]},
        )

    episode_files = list((memory_store._episodes_dir("u1", "cold_attached_idol")).glob("*.md"))
    assert len(episode_files) <= memory_store.MAX_EPISODES


def test_commit_session_persists_session_digest(memory_store):
    memory_store.commit_session(
        user_id="u1",
        persona_name="cold_attached_idol",
        session_id="session-1",
        session_digest={
            "text": "A short but tense conversation.",
            "turn_count": 3,
            "dominant_mood": "withdrawn",
            "key_events": ["rejection_signal"],
        },
        final_state={"relationship_state": {"durable": {"relationship_stage": "guarded"}}, "mood": {"base_mood": "withdrawn"}},
    )

    context = memory_store.load_bootstrap_context(
        user_id="u1",
        persona_name="cold_attached_idol",
        query_context={"user_message": "tense"},
    )

    assert len(context["memory"]["session_digests"]) == 1
    assert context["memory"]["session_digests"][0]["session_id"] == "session-1"
