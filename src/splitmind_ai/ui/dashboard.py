"""Pure helpers for Streamlit dashboard view-models."""

from __future__ import annotations

from typing import Any

from splitmind_ai.drive_signals import build_latent_drive_signature, compute_drive_intensity

RELATIONSHIP_METRICS = (
    "trust",
    "intimacy",
    "distance",
    "tension",
    "attachment_pull",
)

AFFECT_METRICS = (
    "intensity",
    "frustration",
    "carryover",
    "suppression_load",
    "satiation",
)

APPRAISAL_DIMENSIONS = (
    "perceived_acceptance",
    "perceived_rejection",
    "perceived_competition",
    "perceived_distance",
    "ambiguity",
    "face_threat",
    "attachment_activation",
    "repair_opportunity",
)

SELF_STATE_DIMENSIONS = (
    "pride_level",
    "shame_activation",
    "dependency_fear",
    "desire_for_closeness",
    "urge_to_test_user",
)

TIMING_KEYS = (
    ("internal_dynamics", "internal_dynamics_ms"),
    ("social_cue", "social_cue_ms"),
    ("appraisal", "appraisal_ms"),
    ("action_arbitration", "action_arbitration_ms"),
    ("supervisor", "persona_supervisor_ms"),
    ("utterance_planner", "utterance_planner_ms"),
    ("surface_realization", "surface_realization_ms"),
    ("memory_commit", "memory_commit_ms"),
)


def build_turn_snapshot(result: dict[str, Any], turn_number: int) -> dict[str, Any]:
    """Extract a compact dashboard snapshot from the full graph result."""
    relationship = result.get("relationship", {}) or {}
    mood = result.get("mood", {}) or {}
    drive_state = result.get("drive_state", {}) or {}
    inhibition_state = result.get("inhibition_state", {}) or {}
    appraisal = result.get("appraisal", {}) or {}
    self_state = result.get("self_state", {}) or {}
    conversation_policy = result.get("conversation_policy", {}) or {}
    utterance_plan = result.get("utterance_plan", {}) or {}
    trace = result.get("trace", {}) or {}
    internal = result.get("_internal", {}) or {}
    memory = result.get("memory", {}) or {}
    working_memory = result.get("working_memory", {}) or {}

    supervisor_trace = trace.get("supervisor", {}) or {}
    surface_trace = trace.get("surface_realization", {}) or {}
    timing = _extract_timing(trace)
    latent_drive_signature = dict(
        surface_trace.get("latent_drive_signature")
        or build_latent_drive_signature(drive_state, conversation_policy)
    )
    top_drives = _top_drives(drive_state)

    event_flags = (
        internal.get("event_flags")
        or (trace.get("memory_commit", {}) or {}).get("event_flags")
        or (trace.get("internal_dynamics", {}) or {}).get("event_flags")
        or {}
    )

    return {
        "turn": int(turn_number),
        "relationship": {
            **{metric: _bounded_float(relationship.get(metric)) for metric in RELATIONSHIP_METRICS},
            "unresolved_tensions": _top_tensions(relationship.get("unresolved_tensions", [])),
        },
        "mood": {
            "base_mood": mood.get("base_mood"),
            "irritation": _bounded_float(mood.get("irritation")),
            "longing": _bounded_float(mood.get("longing")),
            "protectiveness": _bounded_float(mood.get("protectiveness")),
            "fatigue": _bounded_float(mood.get("fatigue")),
            "openness": _bounded_float(mood.get("openness")),
        },
        "drive": {
            "primary_drive": latent_drive_signature.get("primary_drive"),
            "secondary_drive": latent_drive_signature.get("secondary_drive"),
            "top_target": latent_drive_signature.get("target"),
            "intensity": _bounded_float(
                _first_present(
                    latent_drive_signature.get("intensity"),
                    compute_drive_intensity(drive_state),
                )
            ),
            "frustration": _bounded_float(latent_drive_signature.get("frustration")),
            "carryover": _bounded_float(latent_drive_signature.get("carryover")),
            "suppression_load": _bounded_float(latent_drive_signature.get("suppression_load")),
            "satiation": _bounded_float(latent_drive_signature.get("satiation")),
            "top_drives": top_drives,
            "latent_drive_signature": latent_drive_signature,
        },
        "appraisal": {
            "dominant_appraisal": appraisal.get("dominant_appraisal"),
            "dimensions": {
                dimension: _dimension_score(appraisal.get(dimension))
                for dimension in APPRAISAL_DIMENSIONS
            },
        },
        "self_state": {
            dimension: _bounded_float(self_state.get(dimension))
            for dimension in SELF_STATE_DIMENSIONS
        },
        "policy": {
            "selected_mode": conversation_policy.get("selected_mode"),
            "fallback_mode": conversation_policy.get("fallback_mode"),
            "max_leakage": _bounded_float(conversation_policy.get("max_leakage")),
            "max_directness": _bounded_float(conversation_policy.get("max_directness")),
            "blocked_by_inhibition": list(
                surface_trace.get("blocked_by_inhibition")
                or conversation_policy.get("blocked_by_inhibition", [])
                or inhibition_state.get("blocked_drives", [])
                or []
            ),
            "satisfaction_goal": (
                surface_trace.get("satisfaction_goal")
                or conversation_policy.get("satisfaction_goal")
                or ""
            ),
            "candidates": [
                {
                    "label": candidate.get("label") or candidate.get("mode") or "unknown",
                    "mode": candidate.get("mode"),
                    "score": _bounded_float(candidate.get("score")),
                }
                for candidate in conversation_policy.get("candidates", []) or []
            ],
        },
        "supervisor": {
            "leakage_level": _bounded_float(
                _first_present(
                    utterance_plan.get("leakage_level"),
                    supervisor_trace.get("leakage_level"),
                )
            ),
            "containment_success": _bounded_float(
                _first_present(
                    utterance_plan.get("containment_success"),
                    supervisor_trace.get("containment_success"),
                )
            ),
        },
        "timing": timing,
        "events": [key for key, value in event_flags.items() if bool(value)],
        "memory": {
            "counts": {
                "emotional_memories": len(memory.get("emotional_memories", []) or []),
                "semantic_preferences": len(memory.get("semantic_preferences", []) or []),
                "active_themes": len(working_memory.get("active_themes", []) or []),
            },
            "active_themes": list(working_memory.get("active_themes", []) or [])[:6],
        },
    }


def build_history_rows(turn_snapshots: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build turn-indexed rows for timeseries and event charts."""
    relationship_rows: list[dict[str, Any]] = []
    affect_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []

    for snapshot in sorted(turn_snapshots, key=lambda item: item.get("turn", 0)):
        turn = int(snapshot.get("turn", 0))
        relationship = snapshot.get("relationship", {}) or {}
        drive = snapshot.get("drive", {}) or {}

        for metric in RELATIONSHIP_METRICS:
            relationship_rows.append({
                "turn": turn,
                "metric": metric,
                "value": _bounded_float(relationship.get(metric)),
            })

        for metric in AFFECT_METRICS:
            affect_rows.append({
                "turn": turn,
                "metric": metric,
                "value": _bounded_float(drive.get(metric)),
            })

        for event in snapshot.get("events", []) or []:
            event_rows.append({"turn": turn, "event": event, "value": 1.0})

        timing = snapshot.get("timing", {}) or {}
        for node_name, value in (timing.get("nodes", {}) or {}).items():
            timing_rows.append({
                "turn": turn,
                "metric": node_name,
                "value": float(value),
            })

    return {
        "relationship": relationship_rows,
        "affect": affect_rows,
        "events": event_rows,
        "timing": timing_rows,
    }


def build_current_dashboard(turn_snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the latest-session dashboard view-model."""
    if not turn_snapshots:
        return {
            "turns": 0,
            "current": None,
            "drive_story": "No active drive loop yet.",
            "story_steps": [],
            "candidate_rows": [],
            "event_groups": [],
            "appraisal_radar": [],
            "self_state_radar": [],
            "drive_rows": [],
            "residue_rows": [],
            "unresolved_tensions": [],
            "active_themes": [],
            "memory_counts": {
                "emotional_memories": 0,
                "semantic_preferences": 0,
                "active_themes": 0,
            },
            "timing_rows": [],
        }

    latest = sorted(turn_snapshots, key=lambda item: item.get("turn", 0))[-1]
    story_steps = _build_story_steps(latest)
    return {
        "turns": len(turn_snapshots),
        "current": latest,
        "drive_story": _build_drive_story(latest),
        "story_steps": story_steps,
        "candidate_rows": [
            {
                "label": candidate.get("label", "unknown"),
                "mode": candidate.get("mode"),
                "score": _bounded_float(candidate.get("score")),
            }
            for candidate in latest.get("policy", {}).get("candidates", []) or []
        ],
        "drive_rows": [
            {
                "label": drive.get("name", "unknown"),
                "value": _bounded_float(drive.get("value")),
                "target": drive.get("target") or "",
            }
            for drive in (latest.get("drive", {}) or {}).get("top_drives", []) or []
        ],
        "residue_rows": _build_residue_rows(latest),
        "event_groups": [
            {"turn": snapshot.get("turn", 0), "events": list(snapshot.get("events", []) or [])}
            for snapshot in sorted(turn_snapshots, key=lambda item: item.get("turn", 0))
            if snapshot.get("events")
        ],
        "appraisal_radar": [
            {"axis": axis, "value": _bounded_float(value)}
            for axis, value in (latest.get("appraisal", {}).get("dimensions", {}) or {}).items()
        ],
        "self_state_radar": [
            {"axis": axis, "value": _bounded_float(value)}
            for axis, value in (latest.get("self_state", {}) or {}).items()
        ],
        "unresolved_tensions": _top_tensions(
            (latest.get("relationship", {}) or {}).get("unresolved_tensions", [])
        ),
        "active_themes": list((latest.get("memory", {}) or {}).get("active_themes", []) or []),
        "memory_counts": dict((latest.get("memory", {}) or {}).get("counts", {}) or {}),
        "timing_rows": [
            {"label": label, "value": float(value)}
            for label, value in (latest.get("timing", {}) or {}).get("nodes", {}).items()
        ],
    }


def _dimension_score(value: Any) -> float:
    if isinstance(value, dict):
        value = value.get("score")
    return _bounded_float(value)


def _top_tensions(tensions: Any) -> list[dict[str, Any]]:
    if not isinstance(tensions, list):
        return []
    normalized: list[dict[str, Any]] = []
    for tension in tensions:
        if not isinstance(tension, dict):
            continue
        normalized.append({
            "theme": tension.get("theme", "unknown"),
            "intensity": _bounded_float(tension.get("intensity")),
            "source": tension.get("source"),
        })
    normalized.sort(key=lambda item: item.get("intensity", 0.0), reverse=True)
    return normalized[:3]


def _top_drives(drive_state: dict[str, Any]) -> list[dict[str, Any]]:
    drives = drive_state.get("top_drives", []) or []
    normalized: list[dict[str, Any]] = []
    for drive in drives[:3]:
        if not isinstance(drive, dict):
            continue
        normalized.append({
            "name": drive.get("name", "unknown"),
            "value": _bounded_float(drive.get("value")),
            "target": drive.get("target") or "",
        })
    return normalized


def _build_story_steps(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    drive = snapshot.get("drive", {}) or {}
    policy = snapshot.get("policy", {}) or {}
    supervisor = snapshot.get("supervisor", {}) or {}
    signature = drive.get("latent_drive_signature", {}) or {}
    blocked = list(policy.get("blocked_by_inhibition", []) or [])

    steps = [
        {
            "stage": "Drive",
            "value": str(drive.get("primary_drive") or "none"),
            "note": f"Intensity {drive.get('intensity', 0.0):.2f}",
            "tone": "drive",
        },
        {
            "stage": "Target",
            "value": str(drive.get("top_target") or "unfixed"),
            "note": str(drive.get("secondary_drive") or "single-track"),
            "tone": "target",
        },
        {
            "stage": "Inhibition",
            "value": ", ".join(blocked[:2]) if blocked else "clear",
            "note": (
                f"Suppression {drive.get('suppression_load', 0.0):.2f}"
                if blocked
                else "No visible block"
            ),
            "tone": "block" if blocked else "open",
        },
        {
            "stage": "Mode",
            "value": str(policy.get("selected_mode") or "none"),
            "note": f"Leakage {supervisor.get('leakage_level', 0.0):.2f}",
            "tone": "mode",
        },
        {
            "stage": "Surface",
            "value": str(signature.get("latent_signal_hint") or "contained"),
            "note": str(policy.get("satisfaction_goal") or "hold state"),
            "tone": "surface",
        },
    ]
    return steps


def _build_drive_story(snapshot: dict[str, Any]) -> str:
    drive = snapshot.get("drive", {}) or {}
    policy = snapshot.get("policy", {}) or {}
    signature = drive.get("latent_drive_signature", {}) or {}
    primary_drive = str(drive.get("primary_drive") or "").strip()
    if not primary_drive:
        return "No active drive loop yet."

    target = str(drive.get("top_target") or "an unfixed target")
    selected_mode = str(policy.get("selected_mode") or "an unresolved mode")
    blocked = list(policy.get("blocked_by_inhibition", []) or [])
    latent_signal = str(signature.get("latent_signal_hint") or "contained residue")
    satisfaction_goal = str(policy.get("satisfaction_goal") or "stabilize the interaction")

    story = f"{primary_drive} is aimed at {target}"
    if blocked:
        story += f", held back by {', '.join(blocked[:2])}"
    story += f", then converted into {selected_mode}"
    story += f" with {latent_signal} on the surface"
    story += f". Current goal: {satisfaction_goal}."
    return story


def _build_residue_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    drive = snapshot.get("drive", {}) or {}
    tones = {
        "intensity": "heat",
        "frustration": "risk",
        "carryover": "carry",
        "suppression_load": "block",
        "satiation": "release",
    }
    labels = {
        "intensity": "Intensity",
        "frustration": "Frustration",
        "carryover": "Carryover",
        "suppression_load": "Suppression",
        "satiation": "Satiation",
    }
    rows: list[dict[str, Any]] = []
    for key in AFFECT_METRICS:
        rows.append({
            "key": key,
            "label": labels[key],
            "value": _bounded_float(drive.get(key)),
            "tone": tones[key],
        })
    return rows


def _bounded_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _extract_timing(trace: dict[str, Any]) -> dict[str, Any]:
    nodes: dict[str, float] = {}
    total_ms = 0.0
    for trace_name, timing_key in TIMING_KEYS:
        timing_value = ((trace.get(trace_name, {}) or {}).get(timing_key))
        if timing_value is None:
            continue
        try:
            numeric = float(timing_value)
        except (TypeError, ValueError):
            continue
        nodes[trace_name] = round(numeric, 2)
        total_ms += numeric
    return {
        "nodes": nodes,
        "total_ms": round(total_ms, 2),
    }
