"""Centralized rule-based state update engine for relationship persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

DEFAULT_RULES: dict[str, dict[str, float]] = {
    "reassurance_received": {
        "durable.trust": 0.05,
        "ephemeral.tension": -0.05,
        "durable.repair_depth": 0.03,
    },
    "rejection_signal": {
        "durable.intimacy": -0.04,
        "durable.distance": 0.06,
        "ephemeral.tension": 0.05,
        "ephemeral.interaction_fragility": 0.08,
    },
    "jealousy_trigger": {
        "ephemeral.tension": 0.07,
        "durable.attachment_pull": 0.04,
        "ephemeral.recent_relational_charge": 0.06,
    },
    "affectionate_exchange": {
        "durable.intimacy": 0.06,
        "durable.trust": 0.03,
        "ephemeral.recent_relational_charge": 0.08,
    },
    "prolonged_avoidance": {
        "durable.distance": 0.05,
        "ephemeral.interaction_fragility": 0.06,
    },
    "user_praised_third_party": {
        "ephemeral.tension": 0.05,
        "durable.attachment_pull": 0.03,
        "ephemeral.recent_relational_charge": 0.05,
    },
    "repair_attempt": {
        "ephemeral.tension": -0.06,
        "durable.trust": 0.04,
        "durable.repair_depth": 0.08,
        "ephemeral.turn_local_repair_opening": 0.20,
    },
}

_DESIRE_TO_EMOTION: dict[str, str] = {
    "be_first_for_user": "jealousy",
    "move_closer": "longing",
    "stay_safe": "anxiety",
    "repair_bond": "relief",
    "protect_self": "defensiveness",
    "jealousy": "irritation",
}

_TENSION_ESCALATION_FLAGS = frozenset({
    "jealousy_trigger",
    "user_praised_third_party",
    "rejection_signal",
    "prolonged_avoidance",
})


def apply_relationship_updates(
    relationship_state: dict[str, Any],
    event_flags: dict[str, bool],
    rules: dict[str, dict[str, float]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Apply event-driven deltas to durable and ephemeral relationship state."""
    rules = rules or DEFAULT_RULES
    state = {
        "durable": dict(relationship_state.get("durable", {}) or {}),
        "ephemeral": dict(relationship_state.get("ephemeral", {}) or {}),
    }
    applied: list[str] = []

    for flag, active in event_flags.items():
        if not active:
            continue
        for path, delta in (rules.get(flag) or {}).items():
            section, field = path.split(".", 1)
            bucket = state.get(section, {})
            current = float(bucket.get(field, 0.0) or 0.0)
            bucket[field] = _clamp(current + delta)
            applied.append(f"{flag} -> {path} {delta:+.3f}")

    settle_delta = _relationship_tension_settle(event_flags)
    if settle_delta > 0.0:
        current = float(state["ephemeral"].get("tension", 0.0) or 0.0)
        state["ephemeral"]["tension"] = _clamp(current - settle_delta)
        applied.append(f"natural_settle -> ephemeral.tension {(-settle_delta):+.3f}")

    return state, applied


def update_unresolved_tension_summary(
    unresolved_summary: list[str],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    event_flags: dict[str, bool],
) -> list[str]:
    """Maintain a compact durable summary of unresolved relational tensions."""
    summary = [str(item) for item in unresolved_summary if item][:4]
    event_type = str(appraisal.get("event_type") or "")
    tension_target = str(appraisal.get("target_of_tension") or "")
    dominant_want = str((conflict_state.get("id_impulse") or {}).get("dominant_want") or "")
    residue = str((conflict_state.get("residue") or {}).get("visible_emotion") or "")
    intensity = max(
        float((conflict_state.get("id_impulse") or {}).get("intensity", 0.0) or 0.0),
        float((conflict_state.get("superego_pressure") or {}).get("pressure", 0.0) or 0.0),
        float((conflict_state.get("residue") or {}).get("intensity", 0.0) or 0.0),
    )

    if event_flags.get("repair_attempt") or event_flags.get("reassurance_received"):
        if summary:
            summary = summary[1:]

    if intensity >= 0.5 and (tension_target or dominant_want or residue):
        label = " / ".join(part for part in (event_type, tension_target, dominant_want or residue) if part)
        if label and label not in summary:
            summary.insert(0, label)

    return summary[:4]


def update_mood(
    mood: dict[str, Any],
    event_flags: dict[str, bool],
    decay_turns: int = 3,
) -> dict[str, Any]:
    """Update mood state based on event flags and natural decay."""
    mood = dict(mood)
    mood["turns_since_shift"] = mood.get("turns_since_shift", 0) + 1

    if mood["turns_since_shift"] >= decay_turns:
        for key in ("irritation", "longing", "protectiveness", "fatigue"):
            if key in mood and isinstance(mood[key], (int, float)):
                mood[key] = max(0.0, mood[key] - 0.1)

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
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    session_id: str = "",
    turn_number: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    """Generate memory candidates to persist."""
    candidates: dict[str, list[dict[str, Any]]] = {
        "emotional_memories": [],
        "semantic_preferences": [],
    }
    now = datetime.now().isoformat()
    id_impulse = conflict_state.get("id_impulse", {}) or {}
    residue = conflict_state.get("residue", {}) or {}
    ego_move = conflict_state.get("ego_move", {}) or {}
    dominant_want = str(id_impulse.get("dominant_want") or "")
    intensity = max(
        float(id_impulse.get("intensity", 0.0) or 0.0),
        float(residue.get("intensity", 0.0) or 0.0),
        float((conflict_state.get("superego_pressure", {}) or {}).get("pressure", 0.0) or 0.0),
    )
    event_type = str(appraisal.get("event_type") or "")
    tension_target = str(appraisal.get("target_of_tension") or "")

    if intensity > 0.4 and (dominant_want or event_type):
        candidates["emotional_memories"].append({
            "event": user_message[:300],
            "agent_response": final_response[:300],
            "emotion": _map_desire_to_emotion(dominant_want or residue.get("visible_emotion", "")),
            "trigger": event_type or dominant_want,
            "target": id_impulse.get("target", ""),
            "wound": tension_target,
            "attempted_action": ego_move.get("social_move", ""),
            "action_tendency": ego_move.get("social_move", ""),
            "interaction_outcome": _infer_interaction_outcome(event_flags, event_type),
            "residual_drive": dominant_want,
            "intensity": intensity,
            "session_id": session_id,
            "turn_number": turn_number,
            "created_at": now,
        })

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
    relationship_state: dict[str, Any],
    mood: dict[str, Any],
    event_flags: dict[str, bool],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    request: dict[str, Any],
    response: dict[str, Any],
    rules: dict[str, dict[str, float]] | None = None,
    decay_turns: int = 3,
    session_id: str = "",
    turn_number: int = 0,
    memory_candidates_override: dict[str, list[dict[str, Any]]] | None = None,
    unresolved_tension_summary_override: list[str] | None = None,
) -> dict[str, Any]:
    """Run the complete relationship persistence update pipeline."""
    user_message = request.get("user_message", "")
    final_response_text = response.get("final_response_text", "")

    updated_state, applied = apply_relationship_updates(relationship_state, event_flags, rules)
    updated_state = update_relationship_state(
        relationship_state=updated_state,
        appraisal=appraisal,
        conflict_state=conflict_state,
        event_flags=event_flags,
    )
    if unresolved_tension_summary_override is None:
        updated_state["durable"]["unresolved_tension_summary"] = update_unresolved_tension_summary(
            unresolved_summary=updated_state["durable"].get("unresolved_tension_summary", []) or [],
            appraisal=appraisal,
            conflict_state=conflict_state,
            event_flags=event_flags,
        )
    else:
        updated_state["durable"]["unresolved_tension_summary"] = [
            str(item) for item in unresolved_tension_summary_override if item
        ][:4]

    updated_mood = update_mood(mood, event_flags, decay_turns)

    if memory_candidates_override is None:
        memory_candidates = generate_memory_candidates(
            user_message=user_message,
            final_response=final_response_text,
            event_flags=event_flags,
            appraisal=appraisal,
            conflict_state=conflict_state,
            session_id=session_id,
            turn_number=turn_number,
        )
    else:
        memory_candidates = {
            "emotional_memories": [
                dict(item) for item in memory_candidates_override.get("emotional_memories", [])
            ],
            "semantic_preferences": [
                dict(item) for item in memory_candidates_override.get("semantic_preferences", [])
            ],
        }

    trace = {
        "applied_rules": applied,
        "event_flags": event_flags,
        "relationship_stage": updated_state["durable"].get("relationship_stage", "unfamiliar"),
        "memory_candidates_count": sum(len(v) for v in memory_candidates.values()),
    }

    return {
        "relationship_state": updated_state,
        "mood": updated_mood,
        "memory_candidates": memory_candidates,
        "applied_rules": applied,
        "trace": trace,
    }


def update_relationship_state(
    *,
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    event_flags: dict[str, bool],
) -> dict[str, Any]:
    """Update durable and ephemeral relationship state from appraisal/conflict outcomes."""
    durable = dict(relationship_state.get("durable", {}) or {})
    ephemeral = dict(relationship_state.get("ephemeral", {}) or {})
    event_type = str(appraisal.get("event_type") or "")
    target_of_tension = str(appraisal.get("target_of_tension") or "")
    ego_move = str((conflict_state.get("ego_move") or {}).get("social_move") or "")
    id_intensity = float((conflict_state.get("id_impulse") or {}).get("intensity", 0.0) or 0.0)
    residue_intensity = float((conflict_state.get("residue") or {}).get("intensity", 0.0) or 0.0)

    if event_type in {"exclusive_disclosure", "affection_signal"}:
        durable["intimacy"] = _clamp(float(durable.get("intimacy", 0.0) or 0.0) + 0.04)
        durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.02)
        ephemeral["recent_relational_charge"] = _clamp(
            float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.12
        )
    elif event_type == "repair_offer":
        durable["repair_depth"] = _clamp(float(durable.get("repair_depth", 0.0) or 0.0) + 0.10)
        durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.03)
        ephemeral["turn_local_repair_opening"] = _clamp(
            float(ephemeral.get("turn_local_repair_opening", 0.0) or 0.0) + 0.20
        )
    elif event_type == "distancing":
        durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.06)
        durable["commitment_readiness"] = _clamp(
            float(durable.get("commitment_readiness", 0.0) or 0.0) - 0.05
        )
        ephemeral["interaction_fragility"] = _clamp(
            float(ephemeral.get("interaction_fragility", 0.0) or 0.0) + 0.10
        )
    elif event_type == "commitment_request":
        ephemeral["recent_relational_charge"] = _clamp(
            float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.10
        )
        if ego_move in {"accept_but_hold", "receive_without_chasing", "allow_dependence_but_reframe"}:
            durable["commitment_readiness"] = _clamp(
                float(durable.get("commitment_readiness", 0.0) or 0.0) + 0.05
            )
        else:
            ephemeral["interaction_fragility"] = _clamp(
                float(ephemeral.get("interaction_fragility", 0.0) or 0.0) + 0.06
            )

    if target_of_tension in {"jealousy", "pride", "shame", "status"}:
        ephemeral["tension"] = _clamp(float(ephemeral.get("tension", 0.0) or 0.0) + 0.04)
        ephemeral["recent_relational_charge"] = _clamp(
            float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.04
        )

    if ego_move in {"accept_but_hold", "receive_without_chasing"}:
        durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.01)
        durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) - 0.01)
    elif ego_move in {"acknowledge_without_opening", "withdraw"}:
        durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.02)
        ephemeral["interaction_fragility"] = _clamp(
            float(ephemeral.get("interaction_fragility", 0.0) or 0.0) + 0.04
        )

    if event_flags.get("repair_attempt") or event_flags.get("reassurance_received"):
        durable["commitment_readiness"] = _clamp(
            float(durable.get("commitment_readiness", 0.0) or 0.0) + 0.03
        )

    ephemeral["recent_relational_charge"] = _clamp(
        float(ephemeral.get("recent_relational_charge", 0.0) or 0.0)
        + (id_intensity * 0.05)
        + (residue_intensity * 0.04)
    )

    stage_score = (
        float(durable.get("trust", 0.0) or 0.0) * 0.32
        + float(durable.get("intimacy", 0.0) or 0.0) * 0.24
        + float(durable.get("commitment_readiness", 0.0) or 0.0) * 0.18
        + float(durable.get("repair_depth", 0.0) or 0.0) * 0.10
        + float(durable.get("attachment_pull", 0.0) or 0.0) * 0.10
        - float(durable.get("distance", 0.0) or 0.0) * 0.08
        - float(ephemeral.get("tension", 0.0) or 0.0) * 0.12
        - float(ephemeral.get("interaction_fragility", 0.0) or 0.0) * 0.08
    )
    if stage_score < 0.28:
        durable["relationship_stage"] = "unfamiliar"
    elif stage_score < 0.48:
        durable["relationship_stage"] = "warming"
    elif stage_score < 0.64:
        durable["relationship_stage"] = "charged"
    elif stage_score < 0.80:
        durable["relationship_stage"] = "testing"
    else:
        durable["relationship_stage"] = "mutual"

    ephemeral["escalation_allowed"] = (
        float(durable.get("commitment_readiness", 0.0) or 0.0) >= 0.65
        and float(durable.get("repair_depth", 0.0) or 0.0) >= 0.30
        and durable.get("relationship_stage") in {"testing", "mutual"}
        and float(ephemeral.get("interaction_fragility", 0.0) or 0.0) < 0.45
    )

    return {"durable": durable, "ephemeral": ephemeral}


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


def _map_desire_to_emotion(desire: str) -> str:
    return _DESIRE_TO_EMOTION.get(desire, desire or "mixed_affect")


def _infer_interaction_outcome(event_flags: dict[str, bool], event_type: str) -> str:
    if event_flags.get("repair_attempt") or event_flags.get("reassurance_received") or event_type == "repair_offer":
        return "repair_signal"
    if event_flags.get("jealousy_trigger") or event_flags.get("user_praised_third_party"):
        return "tension_increase"
    if event_flags.get("rejection_signal") or event_flags.get("prolonged_avoidance") or event_type == "distancing":
        return "distance_increase"
    if event_flags.get("affectionate_exchange") or event_type in {"affection_signal", "exclusive_disclosure"}:
        return "bonding"
    return "neutral"
