"""Tests for the centralized state update engine."""

import pytest

from splitmind_ai.rules.state_updates import (
    apply_relationship_updates,
    generate_memory_candidates,
    run_full_update,
    update_mood,
    update_relationship_state,
    update_unresolved_tension_summary,
)


class TestApplyRelationshipUpdates:
    def test_jealousy_trigger_updates_durable_and_ephemeral(self):
        state = {
            "durable": {"trust": 0.5, "intimacy": 0.3, "attachment_pull": 0.3},
            "ephemeral": {"tension": 0.1, "recent_relational_charge": 0.0},
        }
        updated, applied = apply_relationship_updates(
            state, {"jealousy_trigger": True}
        )
        assert updated["ephemeral"]["tension"] == pytest.approx(0.17, abs=0.01)
        assert updated["durable"]["attachment_pull"] == pytest.approx(0.34, abs=0.01)
        assert len(applied) > 0

    def test_reassurance_received_settles_tension(self):
        state = {
            "durable": {"trust": 0.5, "repair_depth": 0.0},
            "ephemeral": {"tension": 0.2},
        }
        updated, _ = apply_relationship_updates(
            state, {"reassurance_received": True}
        )
        assert updated["durable"]["trust"] == pytest.approx(0.55, abs=0.01)
        assert updated["ephemeral"]["tension"] == pytest.approx(0.12, abs=0.01)


class TestUpdateUnresolvedTensionSummary:
    def test_adds_new_summary_when_pressure_is_high(self):
        result = update_unresolved_tension_summary(
            unresolved_summary=[],
            appraisal={"event_type": "repair_offer", "target_of_tension": "pride"},
            conflict_state={
                "id_impulse": {"dominant_want": "move_closer", "intensity": 0.7},
                "superego_pressure": {"pressure": 0.6},
                "residue": {"visible_emotion": "pleased_but_guarded", "intensity": 0.4},
            },
            event_flags={},
        )
        assert len(result) == 1
        assert "repair_offer" in result[0]

    def test_repair_drops_oldest_summary(self):
        result = update_unresolved_tension_summary(
            unresolved_summary=["old tension", "older tension"],
            appraisal={},
            conflict_state={},
            event_flags={"repair_attempt": True},
        )
        assert result == ["older tension"]


class TestUpdateMood:
    def test_jealousy_shifts_to_irritated(self):
        mood = {"base_mood": "calm", "irritation": 0.0, "turns_since_shift": 0}
        result = update_mood(mood, {"jealousy_trigger": True})
        assert result["base_mood"] == "irritated"
        assert result["irritation"] > 0


class TestGenerateMemoryCandidates:
    def test_generates_emotional_memory_from_conflict_state(self):
        result = generate_memory_candidates(
            user_message="I had so much fun with them",
            final_response="Oh really",
            event_flags={"jealousy_trigger": True},
            appraisal={"event_type": "provocation", "target_of_tension": "jealousy"},
            conflict_state={
                "id_impulse": {"dominant_want": "be_first_for_user", "intensity": 0.7, "target": "user"},
                "superego_pressure": {"pressure": 0.6},
                "ego_move": {"social_move": "accept_but_hold"},
                "residue": {"visible_emotion": "irritated", "intensity": 0.5},
            },
            session_id="s1",
            turn_number=3,
        )
        assert len(result["emotional_memories"]) == 1
        em = result["emotional_memories"][0]
        assert em["emotion"] == "jealousy"
        assert em["trigger"] == "provocation"
        assert em["residual_drive"] == "be_first_for_user"


class TestUpdateRelationshipState:
    def test_repair_offer_improves_durable_state(self):
        state = {
            "durable": {
                "trust": 0.5,
                "intimacy": 0.3,
                "distance": 0.5,
                "attachment_pull": 0.3,
                "relationship_stage": "warming",
                "commitment_readiness": 0.2,
                "repair_depth": 0.0,
            },
            "ephemeral": {
                "tension": 0.1,
                "recent_relational_charge": 0.0,
                "escalation_allowed": False,
                "interaction_fragility": 0.1,
                "turn_local_repair_opening": 0.0,
            },
        }
        result = update_relationship_state(
            relationship_state=state,
            appraisal={"event_type": "repair_offer", "target_of_tension": "pride"},
            conflict_state={
                "id_impulse": {"intensity": 0.4},
                "residue": {"intensity": 0.3},
                "ego_move": {"social_move": "accept_but_hold"},
            },
            event_flags={"repair_attempt": True},
        )

        assert result["durable"]["trust"] > 0.5
        assert result["durable"]["repair_depth"] > 0.0
        assert result["ephemeral"]["turn_local_repair_opening"] > 0.0

    def test_commitment_request_handles_dict_ego_move(self):
        state = {
            "durable": {
                "trust": 0.5,
                "intimacy": 0.3,
                "distance": 0.5,
                "attachment_pull": 0.3,
                "relationship_stage": "warming",
                "commitment_readiness": 0.2,
                "repair_depth": 0.0,
            },
            "ephemeral": {
                "tension": 0.1,
                "recent_relational_charge": 0.0,
                "escalation_allowed": False,
                "interaction_fragility": 0.1,
                "turn_local_repair_opening": 0.0,
            },
        }
        result = update_relationship_state(
            relationship_state=state,
            appraisal={"event_type": "commitment_request", "target_of_tension": "status"},
            conflict_state={
                "id_impulse": {"intensity": 0.4},
                "residue": {"intensity": 0.3},
                "ego_move": {"social_move": {"unexpected": "dict"}},
            },
            event_flags={"repair_attempt": True},
        )

        assert result["durable"]["commitment_readiness"] > 0.2


class TestRunFullUpdate:
    def test_full_pipeline(self):
        result = run_full_update(
            relationship_state={
                "durable": {
                    "trust": 0.5,
                    "intimacy": 0.3,
                    "distance": 0.5,
                    "attachment_pull": 0.3,
                    "relationship_stage": "warming",
                    "commitment_readiness": 0.2,
                    "repair_depth": 0.0,
                    "unresolved_tension_summary": [],
                },
                "ephemeral": {
                    "tension": 0.1,
                    "recent_relational_charge": 0.0,
                    "escalation_allowed": False,
                    "interaction_fragility": 0.0,
                    "turn_local_repair_opening": 0.0,
                },
            },
            mood={"base_mood": "calm", "irritation": 0.0, "longing": 0.0, "protectiveness": 0.0, "fatigue": 0.0, "openness": 0.5, "turns_since_shift": 0},
            event_flags={"jealousy_trigger": True},
            appraisal={"event_type": "provocation", "target_of_tension": "jealousy"},
            conflict_state={
                "id_impulse": {"dominant_want": "be_first_for_user", "intensity": 0.7, "target": "user"},
                "superego_pressure": {"pressure": 0.6},
                "ego_move": {"social_move": "accept_but_hold"},
                "residue": {"visible_emotion": "irritated", "intensity": 0.5},
            },
            request={"user_message": "I had fun with others"},
            response={"final_response_text": "Oh really"},
        )

        assert result["relationship_state"]["ephemeral"]["tension"] > 0.1
        assert result["mood"]["base_mood"] == "irritated"
        assert len(result["relationship_state"]["durable"]["unresolved_tension_summary"]) == 1
        assert len(result["memory_candidates"]["emotional_memories"]) == 1
        assert len(result["applied_rules"]) > 0
