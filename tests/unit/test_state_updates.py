"""Tests for the centralized state update engine."""

import pytest

from splitmind_ai.rules.state_updates import (
    apply_relationship_rules,
    generate_memory_candidates,
    run_full_update,
    update_mood,
    update_unresolved_tensions,
)


class TestApplyRelationshipRules:
    def test_jealousy_trigger(self):
        rel = {"trust": 0.5, "intimacy": 0.3, "tension": 0.1, "attachment_pull": 0.3}
        updated, applied = apply_relationship_rules(
            rel, {"jealousy_trigger": True}
        )
        assert updated["tension"] == pytest.approx(0.17, abs=0.01)
        assert updated["attachment_pull"] == pytest.approx(0.34, abs=0.01)
        assert len(applied) > 0

    def test_reassurance_received(self):
        rel = {"trust": 0.5, "tension": 0.2}
        updated, _ = apply_relationship_rules(
            rel, {"reassurance_received": True}
        )
        assert updated["trust"] == pytest.approx(0.55, abs=0.01)
        assert updated["tension"] == pytest.approx(0.12, abs=0.01)

    def test_repair_attempt(self):
        rel = {"trust": 0.5, "tension": 0.3}
        updated, applied = apply_relationship_rules(
            rel, {"repair_attempt": True}
        )
        assert updated["tension"] < 0.3
        assert updated["trust"] > 0.5

    def test_user_praised_third_party(self):
        rel = {"tension": 0.1, "attachment_pull": 0.3}
        updated, _ = apply_relationship_rules(
            rel, {"user_praised_third_party": True}
        )
        assert updated["tension"] > 0.1
        assert updated["attachment_pull"] > 0.3

    def test_no_active_flags(self):
        rel = {"trust": 0.5, "tension": 0.1}
        updated, applied = apply_relationship_rules(
            rel, {"jealousy_trigger": False}
        )
        assert updated["trust"] == 0.5
        assert updated["tension"] == pytest.approx(0.09, abs=0.01)
        assert len(applied) == 1

    def test_values_clamped(self):
        rel = {"trust": 0.99, "tension": 0.01}
        updated, _ = apply_relationship_rules(
            rel, {"reassurance_received": True}
        )
        assert updated["trust"] <= 1.0
        assert updated["tension"] >= 0.0


class TestUpdateUnresolvedTensions:
    def test_adds_new_tension(self):
        result = update_unresolved_tensions(
            unresolved=[],
            dominant_desire="jealousy",
            affective_pressure=0.7,
            user_message="I had fun with others",
            event_flags={},
        )
        assert len(result) == 1
        assert result[0]["theme"] == "jealousy"
        assert "last_reinforced_at" in result[0]

    def test_reinforces_existing(self):
        existing = [{"theme": "jealousy", "intensity": 0.5, "source": "x",
                      "created_at": "2026-01-01", "last_reinforced_at": "2026-01-01"}]
        result = update_unresolved_tensions(
            unresolved=existing,
            dominant_desire="jealousy",
            affective_pressure=0.7,
            user_message="Again",
            event_flags={},
        )
        assert len(result) == 1
        assert result[0]["intensity"] > 0.5

    def test_decays_on_reassurance(self):
        existing = [{"theme": "fear", "intensity": 0.3, "source": "x",
                      "created_at": "2026-01-01", "last_reinforced_at": "2026-01-01"}]
        result = update_unresolved_tensions(
            unresolved=existing,
            dominant_desire="neutral",
            affective_pressure=0.2,
            user_message="You matter",
            event_flags={"reassurance_received": True},
        )
        assert result[0]["intensity"] < 0.3

    def test_passively_decays_without_reinforcement(self):
        existing = [{"theme": "fear", "intensity": 0.3, "source": "x",
                      "created_at": "2026-01-01", "last_reinforced_at": "2026-01-01"}]
        result = update_unresolved_tensions(
            unresolved=existing,
            dominant_desire="neutral",
            affective_pressure=0.2,
            user_message="small talk",
            event_flags={},
        )
        assert result[0]["intensity"] == pytest.approx(0.28, abs=0.01)

    def test_prunes_low_intensity(self):
        existing = [{"theme": "old", "intensity": 0.04, "source": "x",
                      "created_at": "2026-01-01", "last_reinforced_at": "2026-01-01"}]
        result = update_unresolved_tensions(
            unresolved=existing,
            dominant_desire="",
            affective_pressure=0.1,
            user_message="",
            event_flags={},
        )
        assert len(result) == 0

    def test_no_addition_below_threshold(self):
        result = update_unresolved_tensions(
            unresolved=[],
            dominant_desire="jealousy",
            affective_pressure=0.3,  # below 0.5
            user_message="",
            event_flags={},
        )
        assert len(result) == 0


class TestUpdateMood:
    def test_jealousy_shifts_to_irritated(self):
        mood = {"base_mood": "calm", "irritation": 0.0, "turns_since_shift": 0}
        result = update_mood(mood, {"jealousy_trigger": True})
        assert result["base_mood"] == "irritated"
        assert result["irritation"] > 0

    def test_rejection_shifts_to_withdrawn(self):
        mood = {"base_mood": "calm", "turns_since_shift": 0}
        result = update_mood(mood, {"rejection_signal": True})
        assert result["base_mood"] == "withdrawn"

    def test_affectionate_shifts_to_playful(self):
        mood = {"base_mood": "calm", "openness": 0.5, "turns_since_shift": 0}
        result = update_mood(mood, {"affectionate_exchange": True})
        assert result["base_mood"] == "playful"
        assert result["openness"] > 0.5

    def test_reassurance_recovers_from_irritated(self):
        mood = {"base_mood": "irritated", "turns_since_shift": 0}
        result = update_mood(mood, {"reassurance_received": True})
        assert result["base_mood"] == "calm"

    def test_natural_decay_after_turns(self):
        mood = {"base_mood": "irritated", "irritation": 0.5, "longing": 0.3,
                "protectiveness": 0.2, "fatigue": 0.1, "turns_since_shift": 3}
        result = update_mood(mood, {})
        assert result["irritation"] < 0.5
        assert result["longing"] < 0.3

    def test_user_praised_third_party_mood(self):
        mood = {"base_mood": "calm", "irritation": 0.0, "turns_since_shift": 0}
        result = update_mood(mood, {"user_praised_third_party": True})
        assert result["base_mood"] == "irritated"


class TestGenerateMemoryCandidates:
    def test_generates_emotional_memory_on_high_pressure(self):
        result = generate_memory_candidates(
            user_message="I had so much fun with them",
            final_response="Oh really",
            event_flags={"jealousy_trigger": True},
            dynamics={"affective_pressure": 0.7, "dominant_desire": "jealousy"},
            session_id="s1",
            turn_number=3,
        )
        assert len(result["emotional_memories"]) == 1
        em = result["emotional_memories"][0]
        # emotion is mapped from dominant_desire via _map_desire_to_emotion
        assert em["emotion"] == "irritation"
        assert em["trigger"] == "jealousy"
        assert em["session_id"] == "s1"
        assert em["turn_number"] == 3
        assert "agent_response" in em

    def test_emotional_memory_desire_mapping(self):
        result = generate_memory_candidates(
            user_message="Please tell me you care",
            final_response="...",
            event_flags={},
            dynamics={"affective_pressure": 0.6, "dominant_desire": "fear_of_rejection"},
        )
        assert result["emotional_memories"][0]["emotion"] == "anxiety"
        assert result["emotional_memories"][0]["trigger"] == "fear_of_rejection"

    def test_no_memory_on_low_pressure(self):
        result = generate_memory_candidates(
            user_message="Hello",
            final_response="Hi",
            event_flags={},
            dynamics={"affective_pressure": 0.2, "dominant_desire": "neutral"},
        )
        assert len(result["emotional_memories"]) == 0

    def test_semantic_preference_on_affectionate_exchange(self):
        result = generate_memory_candidates(
            user_message="I love talking with you about music",
            final_response="Me too",
            event_flags={"affectionate_exchange": True},
            dynamics={"affective_pressure": 0.3, "dominant_desire": ""},
        )
        assert len(result["semantic_preferences"]) == 1
        assert result["semantic_preferences"][0]["topic"] == "affectionate_context"
        assert "music" in result["semantic_preferences"][0]["preference"]

    def test_no_semantic_preference_without_flag(self):
        result = generate_memory_candidates(
            user_message="Hello",
            final_response="Hi",
            event_flags={},
            dynamics={"affective_pressure": 0.2, "dominant_desire": ""},
        )
        assert len(result["semantic_preferences"]) == 0

    def test_content_length_limits(self):
        long_msg = "x" * 500
        long_resp = "y" * 500
        result = generate_memory_candidates(
            user_message=long_msg,
            final_response=long_resp,
            event_flags={},
            dynamics={"affective_pressure": 0.8, "dominant_desire": "jealousy"},
        )
        em = result["emotional_memories"][0]
        assert len(em["event"]) <= 300
        assert len(em["agent_response"]) <= 300


class TestRunFullUpdate:
    def test_full_pipeline(self):
        result = run_full_update(
            relationship={"trust": 0.5, "intimacy": 0.3, "distance": 0.5,
                           "tension": 0.1, "attachment_pull": 0.3,
                           "unresolved_tensions": []},
            mood={"base_mood": "calm", "irritation": 0.0, "longing": 0.0,
                  "protectiveness": 0.0, "fatigue": 0.0, "openness": 0.5,
                  "turns_since_shift": 0},
            event_flags={"jealousy_trigger": True},
            dynamics={"dominant_desire": "jealousy", "affective_pressure": 0.7},
            request={"user_message": "I had fun with others"},
            response={"final_response_text": "Oh really"},
        )

        assert result["relationship"]["tension"] > 0.1
        assert result["mood"]["base_mood"] == "irritated"
        assert len(result["relationship"]["unresolved_tensions"]) == 1
        assert len(result["memory_candidates"]["emotional_memories"]) == 1
        assert len(result["applied_rules"]) > 0
