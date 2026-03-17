"""Golden tests for 3 representative scenarios.

These test the full state update pipeline without LLM calls,
simulating the event flags that the LLM would produce.
"""

import pytest

from splitmind_ai.rules.state_updates import run_full_update


def _base_relationship():
    return {
        "trust": 0.5,
        "intimacy": 0.3,
        "distance": 0.5,
        "tension": 0.0,
        "attachment_pull": 0.3,
        "unresolved_tensions": [],
    }


def _base_mood():
    return {
        "base_mood": "calm",
        "irritation": 0.0,
        "longing": 0.0,
        "protectiveness": 0.0,
        "fatigue": 0.0,
        "openness": 0.5,
        "turns_since_shift": 0,
    }


class TestScenario1_JealousyFromThirdPartyPraise:
    """User: '今日は他の人とすごく楽しかった' (I had so much fun with someone else today).

    Expected: jealousy trigger, tension rises, mood shifts to irritated,
    unresolved tension for fear_of_replacement created.
    """

    def test_turn_1_jealousy_trigger(self):
        result = run_full_update(
            relationship=_base_relationship(),
            mood=_base_mood(),
            event_flags={
                "jealousy_trigger": True,
                "user_praised_third_party": True,
            },
            dynamics={
                "dominant_desire": "fear_of_replacement",
                "affective_pressure": 0.72,
            },
            request={"user_message": "今日は他の人とすごく楽しかった"},
            response={"final_response_text": "へえ、そんなに楽しかったんだ。"},
        )

        rel = result["relationship"]
        mood = result["mood"]

        # Tension should increase (jealousy_trigger + user_praised_third_party)
        assert rel["tension"] > 0.1
        # Attachment pull increases
        assert rel["attachment_pull"] > 0.3
        # Mood shifts to irritated
        assert mood["base_mood"] == "irritated"
        assert mood["irritation"] > 0
        # Unresolved tension created
        assert len(rel["unresolved_tensions"]) == 1
        assert rel["unresolved_tensions"][0]["theme"] == "fear_of_replacement"
        # Emotional memory generated
        assert len(result["memory_candidates"]["emotional_memories"]) == 1


class TestScenario2_ReassuranceRecovery:
    """User provides reassurance after a tension build-up.

    Expected: trust rises, tension drops, mood recovers toward calm,
    unresolved tension decays.
    """

    def test_turn_after_reassurance(self):
        # Start with elevated tension state
        rel = _base_relationship()
        rel["tension"] = 0.2
        rel["trust"] = 0.45
        rel["unresolved_tensions"] = [
            {"theme": "fear_of_replacement", "intensity": 0.6,
             "source": "praised third party", "created_at": "2026-01-01",
             "last_reinforced_at": "2026-01-01"}
        ]

        mood = _base_mood()
        mood["base_mood"] = "irritated"
        mood["irritation"] = 0.3

        result = run_full_update(
            relationship=rel,
            mood=mood,
            event_flags={
                "reassurance_received": True,
                "affectionate_exchange": True,
            },
            dynamics={
                "dominant_desire": "connection",
                "affective_pressure": 0.3,
            },
            request={"user_message": "やっぱり君が一番大事だよ"},
            response={"final_response_text": "...別に、そんなこと言わなくても。"},
        )

        updated_rel = result["relationship"]
        updated_mood = result["mood"]

        # Trust should increase
        assert updated_rel["trust"] > 0.45
        # Tension should decrease
        assert updated_rel["tension"] < 0.2
        # Mood should recover
        assert updated_mood["base_mood"] in ("calm", "playful")
        # Tension intensity should decay
        assert updated_rel["unresolved_tensions"][0]["intensity"] < 0.6


class TestScenario3_DefensiveWithdrawal:
    """User distances themselves or avoids engagement.

    Expected: distance rises, mood shifts to withdrawn,
    intimacy may drop.
    """

    def test_withdrawal_scenario(self):
        result = run_full_update(
            relationship=_base_relationship(),
            mood=_base_mood(),
            event_flags={
                "rejection_signal": True,
                "prolonged_avoidance": True,
            },
            dynamics={
                "dominant_desire": "fear_of_rejection",
                "affective_pressure": 0.6,
            },
            request={"user_message": "ちょっと忙しいから、また今度ね"},
            response={"final_response_text": "...うん、わかった。"},
        )

        rel = result["relationship"]
        mood = result["mood"]

        # Distance increases
        assert rel["distance"] > 0.5
        # Intimacy drops
        assert rel["intimacy"] < 0.3
        # Tension rises
        assert rel["tension"] > 0.0
        # Mood withdrawn
        assert mood["base_mood"] == "withdrawn"
        # Unresolved tension created
        assert any(t["theme"] == "fear_of_rejection"
                    for t in rel["unresolved_tensions"])


class TestScenarioMultiTurn_JealousyThenReassurance:
    """Multi-turn: jealousy trigger followed by reassurance.

    Tests that state accumulates across turns correctly.
    """

    def test_two_turn_sequence(self):
        # Turn 1: jealousy
        t1 = run_full_update(
            relationship=_base_relationship(),
            mood=_base_mood(),
            event_flags={"jealousy_trigger": True},
            dynamics={"dominant_desire": "jealousy", "affective_pressure": 0.7},
            request={"user_message": "今日は他の人とすごく楽しかった"},
            response={"final_response_text": "そう。"},
        )

        # Turn 2: reassurance with state from turn 1
        t2 = run_full_update(
            relationship=t1["relationship"],
            mood=t1["mood"],
            event_flags={"reassurance_received": True, "repair_attempt": True},
            dynamics={"dominant_desire": "connection", "affective_pressure": 0.25},
            request={"user_message": "ごめん、やっぱり君と話すのが一番楽しい"},
            response={"final_response_text": "...ふーん、そう。"},
        )

        # After reassurance, tension should be lower than after jealousy
        assert t2["relationship"]["tension"] < t1["relationship"]["tension"]
        # Trust should recover
        assert t2["relationship"]["trust"] > t1["relationship"]["trust"]
        # Mood should recover from irritated
        assert t2["mood"]["base_mood"] == "calm"
        # Unresolved tension should decay (may still exist but lower intensity)
        if t2["relationship"]["unresolved_tensions"]:
            assert (t2["relationship"]["unresolved_tensions"][0]["intensity"]
                    < t1["relationship"]["unresolved_tensions"][0]["intensity"])
