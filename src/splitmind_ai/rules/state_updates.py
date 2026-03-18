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
    summary = [
        item
        for item in (_normalize_text_key(value) for value in unresolved_summary)
        if item
    ][:4]
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
            "attempted_action": ego_move.get("move_style", ego_move.get("social_move", "")),
            "action_tendency": ego_move.get("move_style", ego_move.get("social_move", "")),
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
    relationship_state: dict[str, Any] | None = None,
    mood: dict[str, Any] | None = None,
    event_flags: dict[str, bool] | None = None,
    appraisal: dict[str, Any] | None = None,
    conflict_state: dict[str, Any] | None = None,
    turn_shaping_policy: dict[str, Any] | None = None,
    relational_policy: dict[str, Any] | None = None,
    residue_state: dict[str, Any] | None = None,
    repair_policy: dict[str, Any] | None = None,
    comparison_policy: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    relationship: dict[str, Any] | None = None,
    dynamics: dict[str, Any] | None = None,
    rules: dict[str, dict[str, float]] | None = None,
    decay_turns: int = 3,
    session_id: str = "",
    turn_number: int = 0,
    memory_candidates_override: dict[str, list[dict[str, Any]]] | None = None,
    unresolved_tension_summary_override: list[str] | None = None,
) -> dict[str, Any]:
    """Run the complete relationship persistence update pipeline."""
    mood = mood or {}
    event_flags = event_flags or {}
    request = request or {}
    response = response or {}
    if relationship_state is None:
        relationship_state = _normalize_legacy_relationship(relationship or {})
    appraisal = appraisal or _legacy_appraisal_from_flags(event_flags)
    conflict_state = conflict_state or _legacy_conflict_state_from_dynamics(dynamics or {}, appraisal)
    user_message = request.get("user_message", "")
    final_response_text = response.get("final_response_text", "")

    updated_state, applied = apply_relationship_updates(relationship_state, event_flags, rules)
    updated_state = update_relationship_state(
        relationship_state=updated_state,
        appraisal=appraisal,
        conflict_state=conflict_state,
        turn_shaping_policy=turn_shaping_policy or {},
        relational_policy=relational_policy or {},
        residue_state=residue_state or {},
        repair_policy=repair_policy or {},
        comparison_policy=comparison_policy or {},
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
            item
            for item in (_normalize_text_key(value) for value in unresolved_tension_summary_override)
            if item
        ][:4]

    updated_mood = update_mood(mood, event_flags, decay_turns)
    updated_residue_state = update_residue_state(
        residue_state=residue_state or {},
        conflict_state=conflict_state,
        appraisal=appraisal,
        turn_shaping_policy=turn_shaping_policy or {},
        relational_policy=relational_policy or {},
    )

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
                item
                for item in (
                    _coerce_mapping(item)
                    for item in memory_candidates_override.get("emotional_memories", [])
                )
                if item is not None
            ],
            "semantic_preferences": [
                item
                for item in (
                    _coerce_mapping(item)
                    for item in memory_candidates_override.get("semantic_preferences", [])
                )
                if item is not None
            ],
        }

    trace = {
        "applied_rules": applied,
        "event_flags": event_flags,
        "relationship_stage": updated_state["durable"].get("relationship_stage", "unfamiliar"),
        "memory_candidates_count": sum(len(v) for v in memory_candidates.values()),
    }

    return {
        "relationship": _project_legacy_relationship(
            relationship_state=updated_state,
            prior_legacy=relationship or {},
            event_flags=event_flags,
            dynamics=dynamics or {},
        ),
        "relationship_state": updated_state,
        "mood": updated_mood,
        "residue_state": updated_residue_state,
        "memory_candidates": memory_candidates,
        "applied_rules": applied,
        "trace": trace,
    }


def update_relationship_state(
    *,
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    turn_shaping_policy: dict[str, Any] | None = None,
    relational_policy: dict[str, Any] | None = None,
    residue_state: dict[str, Any] | None = None,
    repair_policy: dict[str, Any] | None = None,
    comparison_policy: dict[str, Any] | None = None,
    event_flags: dict[str, bool],
) -> dict[str, Any]:
    """Update durable and ephemeral relationship state from appraisal/conflict outcomes."""
    durable = dict(relationship_state.get("durable", {}) or {})
    ephemeral = dict(relationship_state.get("ephemeral", {}) or {})
    event_type = str(appraisal.get("event_type") or "")
    target_of_tension = str(appraisal.get("target_of_tension") or "")
    ego_move = dict(conflict_state.get("ego_move", {}) or {})
    move_family = str(ego_move.get("move_family") or _legacy_move_family(str(ego_move.get("social_move") or "")))
    id_intensity = float((conflict_state.get("id_impulse") or {}).get("intensity", 0.0) or 0.0)
    residue_intensity = float((conflict_state.get("residue") or {}).get("intensity", 0.0) or 0.0)
    repair_mode = str((repair_policy or {}).get("repair_mode") or "closed")
    comparison_threat = float((comparison_policy or {}).get("comparison_threat_level", 0.0) or 0.0)
    comparison_injury = float((comparison_policy or {}).get("status_injury", 0.0) or 0.0)
    shaping = dict(turn_shaping_policy or {})
    primary_frame = str(shaping.get("primary_frame") or move_family)
    preserved_counterforce = str(shaping.get("preserved_counterforce") or "none")
    policy = dict(relational_policy or {})
    residue_load = float((residue_state or {}).get("overall_load", 0.0) or 0.0)

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
        commitment_style = (
            _normalize_text_key(ego_move.get("social_move"))
            or _normalize_text_key(ego_move.get("move_style"))
            or _normalize_text_key(ego_move.get("move_family"))
            or ""
        )
        if commitment_style in {"accept_but_hold", "receive_without_chasing", "allow_dependence_but_reframe"}:
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

    if move_family in {"repair_acceptance", "affection_receipt"}:
        durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.01)
        durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) - 0.01)
    elif move_family in {"distance_response", "boundary_clarification"}:
        durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.02)
        ephemeral["interaction_fragility"] = _clamp(
            float(ephemeral.get("interaction_fragility", 0.0) or 0.0) + 0.04
        )

    if move_family == "comparison_response":
        ephemeral["tension"] = _clamp(float(ephemeral.get("tension", 0.0) or 0.0) + comparison_threat * 0.08)
        durable["attachment_pull"] = _clamp(float(durable.get("attachment_pull", 0.0) or 0.0) + comparison_injury * 0.04)

    if event_flags.get("repair_attempt") or event_flags.get("reassurance_received"):
        durable["commitment_readiness"] = _clamp(
            float(durable.get("commitment_readiness", 0.0) or 0.0) + 0.03
        )

    ephemeral["repair_mode"] = repair_mode
    _apply_turn_shaping_modulation(
        durable=durable,
        ephemeral=ephemeral,
        primary_frame=primary_frame,
        preserved_counterforce=preserved_counterforce,
        comparison_threat=comparison_threat,
    )

    _apply_persona_modulation(
        durable=durable,
        ephemeral=ephemeral,
        event_type=event_type,
        move_family=move_family,
        relational_policy=policy,
        repair_mode=repair_mode,
        residue_load=residue_load,
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


def update_residue_state(
    *,
    residue_state: dict[str, Any],
    conflict_state: dict[str, Any],
    appraisal: dict[str, Any],
    turn_shaping_policy: dict[str, Any],
    relational_policy: dict[str, Any],
) -> dict[str, Any]:
    """Carry residue across turns with persona-modulated decay."""
    persistence = dict((relational_policy or {}).get("residue_persistence", {}) or {})
    active: list[dict[str, Any]] = []
    for item in list((residue_state or {}).get("active_residues", []) or []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        persona_modifier = float(item.get("persona_modifier", persistence.get(_residue_bucket(label), 0.5)) or 0.5)
        decay = float(item.get("decay", 0.5) or 0.5)
        current = float(item.get("intensity", 0.0) or 0.0)
        next_intensity = max(0.0, min(1.0, current * max(0.0, 1.0 - (decay * (1.0 - persona_modifier * 0.75)))))
        if next_intensity < 0.12:
            continue
        active.append({
            **item,
            "intensity": round(next_intensity, 4),
            "persona_modifier": round(persona_modifier, 4),
        })

    current_residue = dict((conflict_state or {}).get("residue", {}) or {})
    visible_emotion = str(current_residue.get("visible_emotion") or "").strip()
    current_intensity = float(current_residue.get("intensity", 0.0) or 0.0)
    preserved_counterforce = str((turn_shaping_policy or {}).get("preserved_counterforce") or "none")
    counterforce_decay = {
        "status": 0.18,
        "sting": 0.16,
        "pace": 0.26,
        "distance": 0.16,
        "uncertainty": 0.22,
        "none": 0.34,
    }.get(preserved_counterforce, 0.34)
    if visible_emotion and current_intensity >= 0.16:
        bucket = _residue_bucket(visible_emotion)
        active.insert(0, {
            "label": visible_emotion,
            "intensity": round(current_intensity, 4),
            "decay": counterforce_decay,
            "persona_modifier": round(float(persistence.get(bucket, 0.5) or 0.5), 4),
            "linked_theme": str((appraisal or {}).get("target_of_tension") or ""),
            "source_event": str((appraisal or {}).get("event_type") or ""),
        })

    merged: dict[str, dict[str, Any]] = {}
    for item in active:
        label = str(item.get("label") or "")
        previous = merged.get(label)
        if previous is None or float(item.get("intensity", 0.0) or 0.0) >= float(previous.get("intensity", 0.0) or 0.0):
            merged[label] = item

    active_residues = sorted(
        merged.values(),
        key=lambda item: float(item.get("intensity", 0.0) or 0.0),
        reverse=True,
    )[:4]
    overall_load = max((float(item.get("intensity", 0.0) or 0.0) for item in active_residues), default=0.0)
    dominant = str(active_residues[0]["label"]) if active_residues else ""
    trigger_links = list(dict.fromkeys(
        str(item.get("linked_theme") or "")
        for item in active_residues
        if str(item.get("linked_theme") or "").strip()
    ))[:4]
    return {
        "active_residues": active_residues,
        "dominant_residue": dominant,
        "overall_load": round(overall_load, 4),
        "trigger_links": trigger_links,
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


def _normalize_text_key(value: Any) -> str | None:
    """Return a compact string label or None for unsupported values."""
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (int, float, bool)):
        normalized = str(value).strip()
        return normalized or None
    return None


def _coerce_mapping(value: Any) -> dict[str, Any] | None:
    """Best-effort conversion to a dict with string keys."""
    if isinstance(value, dict):
        return {
            str(key): item
            for key, item in value.items()
            if _normalize_text_key(key) is not None
        }
    if isinstance(value, list):
        try:
            mapping = dict(value)
        except (TypeError, ValueError):
            return None
        return {
            str(key): item
            for key, item in mapping.items()
            if _normalize_text_key(key) is not None
        }
    return None


def _apply_persona_modulation(
    *,
    durable: dict[str, Any],
    ephemeral: dict[str, Any],
    event_type: str,
    move_family: str,
    relational_policy: dict[str, Any],
    repair_mode: str,
    residue_load: float,
) -> None:
    repair_style = str(relational_policy.get("repair_style") or "")
    comparison_style = str(relational_policy.get("comparison_style") or "")
    warmth_style = str(relational_policy.get("warmth_release_style") or "")

    if event_type == "repair_offer":
        if repair_style == "cool_accept_with_edge":
            durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.01)
            ephemeral["turn_local_repair_opening"] = _clamp(float(ephemeral.get("turn_local_repair_opening", 0.0) or 0.0) - 0.05)
        elif repair_style == "affectionate_inclusion":
            durable["intimacy"] = _clamp(float(durable.get("intimacy", 0.0) or 0.0) + 0.02)
            ephemeral["recent_relational_charge"] = _clamp(float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.05)
        elif repair_style == "boundaried_reassurance":
            durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.01)
        elif repair_style == "accept_from_above":
            durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.005)
            durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.005)

    if move_family == "comparison_response":
        if comparison_style == "stung_then_withhold":
            durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.015)
            ephemeral["interaction_fragility"] = _clamp(float(ephemeral.get("interaction_fragility", 0.0) or 0.0) + 0.04)
        elif comparison_style == "playful_reclaim":
            ephemeral["recent_relational_charge"] = _clamp(float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.04)
        elif comparison_style == "above_the_frame":
            durable["attachment_pull"] = _clamp(float(durable.get("attachment_pull", 0.0) or 0.0) + 0.02)

    if warmth_style == "quick_rewarding" and repair_mode in {"receptive", "integrative"}:
        ephemeral["recent_relational_charge"] = _clamp(float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.03)
    if warmth_style == "selective_slow" and residue_load >= 0.35:
        durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.01)


def _apply_turn_shaping_modulation(
    *,
    durable: dict[str, Any],
    ephemeral: dict[str, Any],
    primary_frame: str,
    preserved_counterforce: str,
    comparison_threat: float,
) -> None:
    if primary_frame == "repair_acceptance":
        if preserved_counterforce == "status":
            durable["trust"] = _clamp(float(durable.get("trust", 0.0) or 0.0) + 0.005)
            durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.01)
        elif preserved_counterforce == "sting":
            ephemeral["tension"] = _clamp(float(ephemeral.get("tension", 0.0) or 0.0) + 0.02)
        elif preserved_counterforce == "pace":
            ephemeral["turn_local_repair_opening"] = _clamp(float(ephemeral.get("turn_local_repair_opening", 0.0) or 0.0) + 0.04)
            durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) - 0.005)
        elif preserved_counterforce == "distance":
            durable["distance"] = _clamp(float(durable.get("distance", 0.0) or 0.0) + 0.015)

    if primary_frame == "comparison_response":
        if preserved_counterforce == "status":
            ephemeral["tension"] = _clamp(float(ephemeral.get("tension", 0.0) or 0.0) + 0.02 + comparison_threat * 0.04)
        elif preserved_counterforce == "sting":
            ephemeral["interaction_fragility"] = _clamp(float(ephemeral.get("interaction_fragility", 0.0) or 0.0) + 0.03)
        elif preserved_counterforce == "pace":
            ephemeral["recent_relational_charge"] = _clamp(float(ephemeral.get("recent_relational_charge", 0.0) or 0.0) + 0.02)


def _residue_bucket(label: str) -> str:
    lowered = label.lower()
    if "jealous" in lowered or "irrit" in lowered:
        return "jealousy"
    if "hurt" in lowered or "withheld" in lowered:
        return "hurt"
    if "status" in lowered or "pride" in lowered:
        return "status_injury"
    return "warmth"


def _legacy_move_family(style: str) -> str:
    return {
        "accept_but_hold": "repair_acceptance",
        "allow_dependence_but_reframe": "affection_receipt",
        "receive_without_chasing": "affection_receipt",
        "soft_tease_then_receive": "comparison_response",
        "acknowledge_without_opening": "distance_response",
        "withdraw": "distance_response",
    }.get(style, "")


def _normalize_legacy_relationship(relationship: dict[str, Any]) -> dict[str, Any]:
    relationship = dict(relationship or {})
    unresolved = [
        str(item.get("theme") or "")
        for item in list(relationship.get("unresolved_tensions", []) or [])
        if isinstance(item, dict) and str(item.get("theme") or "").strip()
    ]
    return {
        "durable": {
            "trust": float(relationship.get("trust", 0.5) or 0.5),
            "intimacy": float(relationship.get("intimacy", 0.3) or 0.3),
            "distance": float(relationship.get("distance", 0.5) or 0.5),
            "attachment_pull": float(relationship.get("attachment_pull", 0.3) or 0.3),
            "relationship_stage": relationship.get("relationship_stage", "warming") or "warming",
            "commitment_readiness": float(relationship.get("commitment_readiness", 0.0) or 0.0),
            "repair_depth": float(relationship.get("repair_depth", 0.0) or 0.0),
            "unresolved_tension_summary": unresolved,
        },
        "ephemeral": {
            "tension": float(relationship.get("tension", 0.0) or 0.0),
            "recent_relational_charge": float(relationship.get("recent_relational_charge", 0.0) or 0.0),
            "escalation_allowed": bool(relationship.get("escalation_allowed", False)),
            "interaction_fragility": float(relationship.get("interaction_fragility", 0.0) or 0.0),
            "turn_local_repair_opening": float(relationship.get("turn_local_repair_opening", 0.0) or 0.0),
            "repair_mode": str(relationship.get("repair_mode", "closed") or "closed"),
        },
    }


def _legacy_appraisal_from_flags(event_flags: dict[str, bool]) -> dict[str, Any]:
    if event_flags.get("reassurance_received"):
        return {"event_type": "reassurance", "target_of_tension": "closeness"}
    if event_flags.get("repair_attempt"):
        return {"event_type": "repair_offer", "target_of_tension": "pride"}
    if event_flags.get("jealousy_trigger") or event_flags.get("user_praised_third_party"):
        return {"event_type": "provocation", "target_of_tension": "jealousy"}
    if event_flags.get("rejection_signal") or event_flags.get("prolonged_avoidance"):
        return {"event_type": "distancing", "target_of_tension": "safety"}
    if event_flags.get("affectionate_exchange"):
        return {"event_type": "affection_signal", "target_of_tension": "closeness"}
    return {"event_type": "unknown", "target_of_tension": "ambiguity"}


def _legacy_conflict_state_from_dynamics(dynamics: dict[str, Any], appraisal: dict[str, Any]) -> dict[str, Any]:
    dominant = str(dynamics.get("dominant_desire") or "")
    pressure = float(dynamics.get("affective_pressure", 0.0) or 0.0)
    event_type = str((appraisal or {}).get("event_type") or "")
    if event_type in {"repair_offer", "reassurance"}:
        move_style = "accept_but_hold"
    elif event_type == "provocation":
        move_style = "soft_tease_then_receive"
    elif event_type == "distancing":
        move_style = "acknowledge_without_opening"
    else:
        move_style = "receive_without_chasing"
    return {
        "id_impulse": {
            "dominant_want": dominant,
            "secondary_wants": [],
            "intensity": pressure,
            "target": "user",
        },
        "superego_pressure": {
            "forbidden_moves": [],
            "self_image_to_protect": "",
            "pressure": max(0.0, min(1.0, pressure * 0.8)),
            "shame_load": 0.0,
        },
        "ego_move": {
            "move_family": _legacy_move_family(move_style) or "affection_receipt",
            "move_style": move_style,
            "move_rationale": "",
            "dominant_compromise": "",
            "stability": 0.6,
        },
        "residue": {
            "visible_emotion": dominant or "mixed_affect",
            "leak_channel": "",
            "residue_text_intent": "",
            "intensity": pressure,
        },
        "expression_envelope": {
            "length": "short",
            "temperature": "cool_warm",
            "directness": 0.3,
            "closure": 0.4,
        },
    }


def _project_legacy_relationship(
    *,
    relationship_state: dict[str, Any],
    prior_legacy: dict[str, Any],
    event_flags: dict[str, bool],
    dynamics: dict[str, Any],
) -> dict[str, Any]:
    durable = dict((relationship_state or {}).get("durable", {}) or {})
    ephemeral = dict((relationship_state or {}).get("ephemeral", {}) or {})
    unresolved = _update_legacy_unresolved_tensions(
        prior=list(prior_legacy.get("unresolved_tensions", []) or []),
        event_flags=event_flags,
        dynamics=dynamics,
    )
    return {
        "trust": float(durable.get("trust", 0.0) or 0.0),
        "intimacy": float(durable.get("intimacy", 0.0) or 0.0),
        "distance": float(durable.get("distance", 0.0) or 0.0),
        "tension": float(ephemeral.get("tension", 0.0) or 0.0),
        "attachment_pull": float(durable.get("attachment_pull", 0.0) or 0.0),
        "unresolved_tensions": unresolved,
    }


def _update_legacy_unresolved_tensions(
    *,
    prior: list[dict[str, Any]],
    event_flags: dict[str, bool],
    dynamics: dict[str, Any],
) -> list[dict[str, Any]]:
    updated = [item for item in (_coerce_mapping(item) for item in prior) if item is not None]
    if event_flags.get("reassurance_received") or event_flags.get("repair_attempt"):
        for item in updated:
            item["intensity"] = round(float(item.get("intensity", 0.5) or 0.5) * 0.7, 4)
        return updated[:4]

    dominant = str(dynamics.get("dominant_desire") or "")
    pressure = float(dynamics.get("affective_pressure", 0.0) or 0.0)
    if dominant:
        updated.insert(0, {
            "theme": dominant,
            "intensity": round(pressure or 0.5, 4),
            "source": "legacy_projection",
        })
    return updated[:4]
