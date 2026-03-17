"""Centralized rule-based state update engine.

All relationship / mood / unresolved tension update logic lives here.
MemoryCommitNode delegates to this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Default event-flag → state-delta rules (overridable via settings)
DEFAULT_RULES: dict[str, dict[str, float]] = {
    "reassurance_received": {"trust": 0.05, "tension": -0.05},
    "rejection_signal": {"intimacy": -0.04, "distance": 0.06, "tension": 0.05},
    "jealousy_trigger": {"tension": 0.07, "attachment_pull": 0.04},
    "affectionate_exchange": {"intimacy": 0.06, "trust": 0.03},
    "prolonged_avoidance": {"distance": 0.05},
    "user_praised_third_party": {"tension": 0.05, "attachment_pull": 0.03},
    "repair_attempt": {"tension": -0.06, "trust": 0.04},
}

# Themes that can appear as unresolved tensions
TENSION_THEMES = frozenset({
    "fear_of_replacement",
    "fear_of_rejection",
    "need_for_reassurance",
    "shame_after_exposure",
})

# dominant_desire -> emotion label mapping
_DESIRE_TO_EMOTION: dict[str, str] = {
    "fear_of_replacement": "longing",
    "need_for_reassurance": "longing",
    "fear_of_rejection": "anxiety",
    "shame_after_exposure": "shame",
    "attachment_pull": "longing",
    "jealousy": "irritation",
    "protectiveness": "protectiveness",
}

_TENSION_ESCALATION_FLAGS = frozenset({
    "jealousy_trigger",
    "user_praised_third_party",
    "rejection_signal",
    "prolonged_avoidance",
})


def _map_desire_to_emotion(desire: str) -> str:
    return _DESIRE_TO_EMOTION.get(desire, desire)


def apply_relationship_rules(
    relationship: dict[str, Any],
    event_flags: dict[str, bool],
    rules: dict[str, dict[str, float]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Apply event-flag rules to relationship state.

    Returns:
        Tuple of (updated relationship dict, list of applied rule descriptions).
    """
    rules = rules or DEFAULT_RULES
    relationship = dict(relationship)  # shallow copy
    applied: list[str] = []

    for flag, active in event_flags.items():
        if not active:
            continue
        deltas = rules.get(flag, {})
        for field, delta in deltas.items():
            if field in relationship and isinstance(relationship[field], (int, float)):
                relationship[field] = _clamp(relationship[field] + delta)
                applied.append(f"{flag} -> {field} {delta:+.3f}")

    if "tension" in relationship and isinstance(relationship["tension"], (int, float)):
        settle_delta = _relationship_tension_settle(event_flags)
        if settle_delta > 0.0:
            relationship["tension"] = _clamp(relationship["tension"] - settle_delta)
            applied.append(f"natural_settle -> tension {(-settle_delta):+.3f}")

    return relationship, applied


def update_unresolved_tensions(
    unresolved: list[dict[str, Any]],
    dominant_desire: str,
    affective_pressure: float,
    user_message: str,
    event_flags: dict[str, bool],
) -> list[dict[str, Any]]:
    """Manage unresolved tension list: add, reinforce, decay, prune."""
    unresolved = [dict(t) for t in unresolved]  # deep-ish copy
    now = datetime.now().isoformat()

    # Add or reinforce tension when pressure is high
    if affective_pressure > 0.5 and dominant_desire:
        existing = next(
            (t for t in unresolved if t.get("theme") == dominant_desire), None
        )
        if existing:
            existing["intensity"] = min(1.0, existing["intensity"] + 0.08)
            existing["last_reinforced_at"] = now
        else:
            unresolved.append({
                "theme": dominant_desire,
                "intensity": affective_pressure,
                "source": user_message[:100],
                "created_at": now,
                "last_reinforced_at": now,
            })

    # Passive decay every turn; stronger decay when repair signals land.
    for tension in unresolved:
        decay = 0.02
        if event_flags.get("reassurance_received"):
            decay += 0.06
        if event_flags.get("repair_attempt"):
            decay += 0.07
        if affective_pressure > 0.5 and tension.get("theme") == dominant_desire:
            decay = max(0.0, decay - 0.02)
        tension["intensity"] = max(0.0, tension["intensity"] - decay)

    # Prune resolved tensions
    unresolved = [t for t in unresolved if t["intensity"] > 0.05]
    unresolved.sort(key=lambda item: item.get("intensity", 0.0), reverse=True)

    return unresolved


def update_mood(
    mood: dict[str, Any],
    event_flags: dict[str, bool],
    decay_turns: int = 3,
) -> dict[str, Any]:
    """Update mood state based on event flags and natural decay."""
    mood = dict(mood)
    mood["turns_since_shift"] = mood.get("turns_since_shift", 0) + 1

    # Natural decay toward calm
    if mood["turns_since_shift"] >= decay_turns:
        for key in ("irritation", "longing", "protectiveness", "fatigue"):
            if key in mood and isinstance(mood[key], (int, float)):
                mood[key] = max(0.0, mood[key] - 0.1)

    # Event-driven mood shifts (priority order)
    if event_flags.get("jealousy_trigger") or event_flags.get("user_praised_third_party"):
        mood["base_mood"] = "irritated"
        mood["irritation"] = min(1.0, mood.get("irritation", 0.0) + 0.2)
        mood["turns_since_shift"] = 0
    elif event_flags.get("rejection_signal") or event_flags.get("prolonged_avoidance"):
        mood["base_mood"] = "withdrawn"
        mood["turns_since_shift"] = 0
    elif event_flags.get("affectionate_exchange"):
        mood["base_mood"] = "playful"
        mood["openness"] = min(1.0, mood.get("openness", 0.5) + 0.1)
        mood["turns_since_shift"] = 0
    elif event_flags.get("reassurance_received") or event_flags.get("repair_attempt"):
        if mood.get("base_mood") in ("irritated", "withdrawn", "defensive"):
            mood["base_mood"] = "calm"
            mood["turns_since_shift"] = 0

    return mood


def generate_memory_candidates(
    user_message: str,
    final_response: str,
    event_flags: dict[str, bool],
    dynamics: dict[str, Any],
    session_id: str = "",
    turn_number: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    """Generate memory candidates to persist (emotional memories, preferences).

    Returns dict with keys: emotional_memories, semantic_preferences.
    """
    candidates: dict[str, list[dict[str, Any]]] = {
        "emotional_memories": [],
        "semantic_preferences": [],
    }
    now = datetime.now().isoformat()
    affective = dynamics.get("affective_pressure", 0.0)
    dominant = dynamics.get("dominant_desire", "")

    # Emotional memory: save if affective pressure is notable
    if affective > 0.4 and dominant:
        candidates["emotional_memories"].append({
            "event": user_message[:300],
            "agent_response": final_response[:300],
            "emotion": _map_desire_to_emotion(dominant),
            "trigger": dominant,
            "wound": _infer_wound_from_desire(dominant),
            "action_tendency": _infer_action_tendency(dominant),
            "interaction_outcome": _infer_interaction_outcome(event_flags),
            "intensity": affective,
            "session_id": session_id,
            "turn_number": turn_number,
            "created_at": now,
        })

    # Semantic preference: save on affectionate exchange
    if event_flags.get("affectionate_exchange") and user_message:
        candidates["semantic_preferences"].append({
            "topic": "affectionate_context",
            "preference": user_message[:150],
            "evidence": final_response[:120],
            "episode_hint": user_message[:120],
            "confidence": 0.6,
            "created_at": now,
        })

    return candidates


def run_full_update(
    relationship: dict[str, Any],
    mood: dict[str, Any],
    event_flags: dict[str, bool],
    dynamics: dict[str, Any],
    request: dict[str, Any],
    response: dict[str, Any],
    rules: dict[str, dict[str, float]] | None = None,
    decay_turns: int = 3,
    session_id: str = "",
    turn_number: int = 0,
) -> dict[str, Any]:
    """Run the complete state update pipeline.

    Returns a dict with keys:
        relationship, mood, unresolved_tensions, memory_candidates,
        applied_rules, trace
    """
    user_message = request.get("user_message", "")
    final_response_text = response.get("final_response_text", "")

    # 1. Relationship rules
    updated_rel, applied = apply_relationship_rules(relationship, event_flags, rules)

    # 2. Unresolved tensions
    unresolved = update_unresolved_tensions(
        unresolved=updated_rel.get("unresolved_tensions", []),
        dominant_desire=dynamics.get("dominant_desire", ""),
        affective_pressure=dynamics.get("affective_pressure", 0.0),
        user_message=user_message,
        event_flags=event_flags,
    )
    updated_rel["unresolved_tensions"] = unresolved

    # 3. Mood
    updated_mood = update_mood(mood, event_flags, decay_turns)

    # 4. Memory candidates
    memory_candidates = generate_memory_candidates(
        user_message=user_message,
        final_response=final_response_text,
        event_flags=event_flags,
        dynamics=dynamics,
        session_id=session_id,
        turn_number=turn_number,
    )

    trace = {
        "applied_rules": applied,
        "event_flags": event_flags,
        "unresolved_tensions_count": len(unresolved),
        "memory_candidates_count": sum(len(v) for v in memory_candidates.values()),
    }

    return {
        "relationship": updated_rel,
        "mood": updated_mood,
        "unresolved_tensions": unresolved,
        "memory_candidates": memory_candidates,
        "applied_rules": applied,
        "trace": trace,
    }


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _relationship_tension_settle(event_flags: dict[str, bool]) -> float:
    settle = 0.0
    if not any(event_flags.get(flag) for flag in _TENSION_ESCALATION_FLAGS):
        settle += 0.01
    if event_flags.get("reassurance_received"):
        settle += 0.02
    if event_flags.get("repair_attempt"):
        settle += 0.03
    return settle


def _infer_wound_from_desire(dominant_desire: str) -> str:
    wound_by_desire = {
        "jealousy": "special_to_user",
        "fear_of_replacement": "replaceable",
        "fear_of_rejection": "unwanted",
        "need_for_reassurance": "uncertain_bond",
        "shame_after_exposure": "loss_of_face",
    }
    return wound_by_desire.get(dominant_desire, dominant_desire)


def _infer_action_tendency(dominant_desire: str) -> str:
    tendency_by_desire = {
        "jealousy": "test_user",
        "fear_of_replacement": "pull_closer",
        "fear_of_rejection": "withdraw",
        "need_for_reassurance": "seek_repair",
        "shame_after_exposure": "conceal",
    }
    return tendency_by_desire.get(dominant_desire, "monitor")


def _infer_interaction_outcome(event_flags: dict[str, bool]) -> str:
    if event_flags.get("repair_attempt") or event_flags.get("reassurance_received"):
        return "repair_signal"
    if event_flags.get("jealousy_trigger") or event_flags.get("user_praised_third_party"):
        return "tension_increase"
    if event_flags.get("rejection_signal") or event_flags.get("prolonged_avoidance"):
        return "distance_increase"
    if event_flags.get("affectionate_exchange"):
        return "bonding"
    return "neutral"
