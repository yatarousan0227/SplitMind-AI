"""Pure helpers for Streamlit dashboard view-models."""

from __future__ import annotations

import json
from typing import Any

RELATIONSHIP_METRICS = (
    "trust",
    "intimacy",
    "distance",
    "tension",
    "attachment_pull",
)

AFFECT_METRICS = (
    "id_intensity",
    "superego_pressure",
    "residue_intensity",
    "directness",
    "closure",
)

CONFLICT_SIGNAL_METRICS = (
    "id_intensity",
    "superego_pressure",
    "stability",
    "residue_intensity",
    "directness",
    "closure",
)

APPRAISAL_DIMENSIONS = (
    "confidence",
    "stakes",
    "closeness_axis",
    "pride_axis",
    "jealousy_axis",
    "ambiguity_axis",
)

TIMING_KEYS = (
    ("appraisal", "appraisal_ms"),
    ("conflict_engine", "conflict_engine_ms"),
    ("expression_realizer", "expression_realizer_ms"),
    ("fidelity_gate", "fidelity_gate_ms"),
    ("memory_interpreter", "memory_interpreter_ms"),
    ("memory_commit", "memory_commit_ms"),
)


def build_turn_snapshot(result: dict[str, Any], turn_number: int) -> dict[str, Any]:
    """Extract a compact dashboard snapshot from the full graph result."""
    relationship_state = result.get("relationship_state", {}) or {}
    durable = relationship_state.get("durable", {}) or {}
    ephemeral = relationship_state.get("ephemeral", {}) or {}
    mood = result.get("mood", {}) or {}
    appraisal = result.get("appraisal", {}) or {}
    conflict_state = result.get("conflict_state", {}) or {}
    trace = result.get("trace", {}) or {}
    memory = result.get("memory", {}) or {}
    working_memory = result.get("working_memory", {}) or {}
    fidelity_trace = trace.get("fidelity_gate", {}) or {}
    expression_trace = trace.get("expression_realizer", {}) or {}
    timing = _extract_timing(trace)
    envelope = conflict_state.get("expression_envelope", {}) or {}
    id_impulse = conflict_state.get("id_impulse", {}) or {}
    superego = conflict_state.get("superego_pressure", {}) or {}
    ego_move = conflict_state.get("ego_move", {}) or {}
    residue = conflict_state.get("residue", {}) or {}
    appraisal_dimensions = _appraisal_dimensions(appraisal)

    working_memory_themes = _normalize_theme_list(working_memory.get("active_themes", []))

    return {
        "turn": int(turn_number),
        "relationship": {
            "trust": _bounded_float(durable.get("trust")),
            "intimacy": _bounded_float(durable.get("intimacy")),
            "distance": _bounded_float(durable.get("distance")),
            "tension": _bounded_float(ephemeral.get("tension")),
            "attachment_pull": _bounded_float(durable.get("attachment_pull")),
            "unresolved_tensions": _top_tensions(durable.get("unresolved_tension_summary", [])),
        },
        "mood": {
            "base_mood": mood.get("base_mood"),
            "irritation": _bounded_float(mood.get("irritation")),
            "longing": _bounded_float(mood.get("longing")),
            "protectiveness": _bounded_float(mood.get("protectiveness")),
            "fatigue": _bounded_float(mood.get("fatigue")),
            "openness": _bounded_float(mood.get("openness")),
        },
        "appraisal": {
            "event_type": appraisal.get("event_type") or "",
            "valence": appraisal.get("valence") or "",
            "target_of_tension": appraisal.get("target_of_tension") or "",
            "stakes": appraisal.get("stakes") or "",
            "confidence": _bounded_float(appraisal.get("confidence")),
            "summary_short": appraisal.get("summary_short") or "",
            "dimensions": appraisal_dimensions,
            "active_themes": _normalize_theme_list(appraisal.get("active_themes", [])),
        },
        "conflict": {
            "dominant_want": id_impulse.get("dominant_want") or "",
            "target": id_impulse.get("target") or "",
            "id_intensity": _bounded_float(id_impulse.get("intensity")),
            "forbidden_moves": list(superego.get("forbidden_moves", []) or [])[:4],
            "self_image_to_protect": superego.get("self_image_to_protect") or "",
            "superego_pressure": _bounded_float(superego.get("pressure")),
            "shame_load": _bounded_float(superego.get("shame_load")),
            "move_family": ego_move.get("move_family") or "",
            "move_style": ego_move.get("move_style") or "",
            "move_rationale": ego_move.get("move_rationale") or "",
            "stability": _bounded_float(ego_move.get("stability")),
            "visible_emotion": residue.get("visible_emotion") or "",
            "leak_channel": residue.get("leak_channel") or "",
            "residue_intensity": _bounded_float(residue.get("intensity")),
        },
        "expression": {
            "length": envelope.get("length") or "",
            "temperature": envelope.get("temperature") or "",
            "directness": _bounded_float(envelope.get("directness")),
            "closure": _bounded_float(envelope.get("closure")),
            "used_llm": bool(expression_trace.get("used_llm", False)),
        },
        "pacing": {
            "relationship_stage": durable.get("relationship_stage") or "",
            "commitment_readiness": _bounded_float(durable.get("commitment_readiness")),
            "repair_depth": _bounded_float(durable.get("repair_depth")),
            "escalation_allowed": bool(ephemeral.get("escalation_allowed", False)),
        },
        "fidelity": {
            "passed": bool(fidelity_trace.get("passed", False)),
            "move_fidelity": _bounded_float(fidelity_trace.get("move_fidelity")),
            "residue_fidelity": _bounded_float(fidelity_trace.get("residue_fidelity")),
            "structural_persona_fidelity": _bounded_float(fidelity_trace.get("structural_persona_fidelity")),
            "anti_exposition": _bounded_float(fidelity_trace.get("anti_exposition")),
            "hard_safety": _bounded_float(fidelity_trace.get("hard_safety")),
            "warnings": list(fidelity_trace.get("warnings", []) or [])[:4],
        },
        "timing": timing,
        "events": [str(appraisal.get("event_type"))] if appraisal.get("event_type") else [],
        "memory": {
            "counts": {
                "emotional_memories": len(memory.get("emotional_memories", []) or []),
                "semantic_preferences": len(memory.get("semantic_preferences", []) or []),
                "active_themes": len(working_memory_themes),
            },
            "active_themes": working_memory_themes,
        },
    }


def build_history_rows(turn_snapshots: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build turn-indexed rows for timeseries and event charts."""
    relationship_rows: list[dict[str, Any]] = []
    affect_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    surface_rows: list[dict[str, Any]] = []

    for snapshot in sorted(turn_snapshots, key=lambda item: item.get("turn", 0)):
        turn = int(snapshot.get("turn", 0))
        relationship = snapshot.get("relationship", {}) or {}
        conflict = snapshot.get("conflict", {}) or {}

        for metric in RELATIONSHIP_METRICS:
            relationship_rows.append({
                "turn": turn,
                "metric": metric,
                "value": _bounded_float(relationship.get(metric)),
            })

        for metric in CONFLICT_SIGNAL_METRICS:
            affect_rows.append({
                "turn": turn,
                "metric": metric,
                "value": _bounded_float(conflict.get(metric) if metric in conflict else (snapshot.get("expression", {}) or {}).get(metric)),
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

        conflict = snapshot.get("conflict", {}) or {}
        pacing = snapshot.get("pacing", {}) or {}
        social_move = str(conflict.get("move_style") or "")
        relationship_stage = str(pacing.get("relationship_stage") or "")
        if social_move:
            surface_rows.append({
                "turn": turn,
                "metric": "move_style",
                "value": social_move,
            })
        if relationship_stage:
            surface_rows.append({
                "turn": turn,
                "metric": "relationship_stage",
                "value": relationship_stage,
            })

    return {
        "relationship": relationship_rows,
        "affect": affect_rows,
        "events": event_rows,
        "timing": timing_rows,
        "surface": surface_rows,
    }


def build_current_dashboard(turn_snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the latest-session dashboard view-model."""
    if not turn_snapshots:
        return {
            "turns": 0,
            "current": None,
            "conflict_story": "No active conflict loop yet.",
            "story_steps": [],
            "event_groups": [],
            "appraisal_radar": [],
            "conflict_profile_rows": [],
            "conflict_rows": [],
            "expression_rows": [],
            "pacing_rows": [],
            "fidelity_rows": [],
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
        "conflict_story": _build_conflict_story(latest),
        "story_steps": story_steps,
        "conflict_profile_rows": _build_conflict_profile_rows(latest),
        "conflict_rows": _build_conflict_rows(latest),
        "expression_rows": _build_expression_rows(latest),
        "pacing_rows": _build_pacing_rows(latest),
        "fidelity_rows": _build_fidelity_rows(latest),
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
        if isinstance(tension, str):
            normalized.append({"theme": tension, "intensity": 0.5, "source": ""})
        elif isinstance(tension, dict):
            theme = _normalize_theme_item(
                tension.get("theme")
                or tension.get("label")
                or tension.get("name")
                or tension.get("target")
                or tension
            )
            normalized.append({
                "theme": theme or "unknown",
                "intensity": _bounded_float(tension.get("intensity")),
                "source": _summarize_source(tension.get("source")),
            })
    return normalized[:3]


def _normalize_theme_list(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    for item in items:
        label = _normalize_theme_item(item)
        if label and label not in normalized:
            normalized.append(label)
    return normalized[:6]


def _normalize_theme_item(item: Any) -> str:
    if isinstance(item, str):
        return _truncate_text(item.strip(), limit=60)

    if isinstance(item, dict):
        for key in ("theme", "label", "name", "target", "value", "event_type", "source"):
            value = item.get(key)
            if value:
                normalized = _normalize_theme_item(value)
                if normalized:
                    return normalized
        serialized = json.dumps(item, ensure_ascii=False, default=str)
        return _truncate_text(serialized, limit=60)

    if isinstance(item, (list, tuple, set)):
        parts = [_normalize_theme_item(value) for value in list(item)[:3]]
        filtered = [part for part in parts if part]
        return _truncate_text(" / ".join(filtered), limit=60)

    if item is None:
        return ""

    return _truncate_text(str(item), limit=60)


def _summarize_source(source: Any) -> str:
    if isinstance(source, str):
        return _truncate_text(source.strip(), limit=96)

    if isinstance(source, dict):
        for key in ("source", "summary", "text", "message", "content"):
            value = source.get(key)
            if value:
                return _summarize_source(value)
        parts = []
        for key in ("theme", "target", "name", "label"):
            value = source.get(key)
            if value:
                normalized = _normalize_theme_item(value)
                if normalized:
                    parts.append(normalized)
        if parts:
            return _truncate_text(" / ".join(parts), limit=96)
        return ""

    if isinstance(source, (list, tuple, set)):
        parts = [_summarize_source(item) for item in list(source)[:3]]
        filtered = [part for part in parts if part]
        return _truncate_text(" / ".join(filtered), limit=96)

    if source is None:
        return ""

    return _truncate_text(str(source), limit=96)


def _truncate_text(text: str, *, limit: int) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[: limit - 1].rstrip()}…"


def _build_story_steps(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    appraisal = snapshot.get("appraisal", {}) or {}
    conflict = snapshot.get("conflict", {}) or {}
    expression = snapshot.get("expression", {}) or {}
    pacing = snapshot.get("pacing", {}) or {}
    fidelity = snapshot.get("fidelity", {}) or {}
    blocked = list(conflict.get("forbidden_moves", []) or [])

    steps = [
        {
            "stage": "Appraisal",
            "value": str(appraisal.get("event_type") or "none"),
            "note": f"Confidence {appraisal.get('confidence', 0.0):.2f}",
            "tone": "drive",
        },
        {
            "stage": "Tension",
            "value": str(appraisal.get("target_of_tension") or "unfixed"),
            "note": str(appraisal.get("stakes") or "low"),
            "tone": "target",
        },
        {
            "stage": "Superego",
            "value": ", ".join(blocked[:2]) if blocked else "clear",
            "note": (
                f"Pressure {conflict.get('superego_pressure', 0.0):.2f}"
                if blocked
                else "No visible block"
            ),
            "tone": "block" if blocked else "open",
        },
        {
            "stage": "Ego Move",
            "value": str(conflict.get("move_style") or "none"),
            "note": f"Stability {conflict.get('stability', 0.0):.2f}",
            "tone": "mode",
        },
        {
            "stage": "Expression",
            "value": str(expression.get("temperature") or "contained"),
            "note": str(conflict.get("visible_emotion") or "hold state"),
            "tone": "surface",
        },
        {
            "stage": "Fidelity",
            "value": "pass" if fidelity.get("passed") else "warn",
            "note": (
                f"anti-exposition {fidelity.get('anti_exposition', 0.0):.2f}"
                if fidelity
                else "not checked"
            ),
            "tone": "target",
        },
        {
            "stage": "Relationship",
            "value": str(pacing.get("relationship_stage") or "untracked"),
            "note": (
                "escalation allowed"
                if pacing.get("escalation_allowed")
                else "escalation held"
            ),
            "tone": "target",
        },
    ]
    return steps


def _build_conflict_story(snapshot: dict[str, Any]) -> str:
    conflict = snapshot.get("conflict", {}) or {}
    appraisal = snapshot.get("appraisal", {}) or {}
    dominant_want = str(conflict.get("dominant_want") or "").strip()
    if not dominant_want:
        return "No active conflict loop yet."

    target = str(conflict.get("target") or "an unfixed target")
    social_move = str(conflict.get("move_style") or "an unresolved move")
    blocked = list(conflict.get("forbidden_moves", []) or [])
    residue = str(conflict.get("visible_emotion") or "contained residue")
    story = f"{dominant_want} is aimed at {target}"
    if blocked:
        story += f", held back by {', '.join(blocked[:2])}"
    story += f", then converted into {social_move}"
    story += f" with {residue} left on the surface"
    if appraisal.get("summary_short"):
        story += f". Appraisal: {appraisal.get('summary_short')}."
    return story


def _build_residue_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    conflict = snapshot.get("conflict", {}) or {}
    expression = snapshot.get("expression", {}) or {}
    tones = {
        "id_intensity": "heat",
        "superego_pressure": "risk",
        "residue_intensity": "carry",
        "directness": "block",
        "closure": "release",
    }
    labels = {
        "id_intensity": "Id Intensity",
        "superego_pressure": "Superego Pressure",
        "residue_intensity": "Residue Intensity",
        "directness": "Directness",
        "closure": "Closure",
    }
    rows: list[dict[str, Any]] = []
    for key in AFFECT_METRICS:
        rows.append({
            "key": key,
            "label": labels[key],
            "value": _bounded_float(conflict.get(key) if key in conflict else expression.get(key)),
            "tone": tones[key],
        })
    return rows


def _build_conflict_profile_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    conflict = snapshot.get("conflict", {}) or {}
    expression = snapshot.get("expression", {}) or {}
    forbidden_moves = list(conflict.get("forbidden_moves", []) or [])

    return [
        {
            "key": "id_profile",
            "label": "Id",
            "value": str(conflict.get("dominant_want") or "none"),
            "meter_label": "Id Intensity",
            "meter_value": _bounded_float(conflict.get("id_intensity")),
            "tone": "heat",
            "target": str(conflict.get("target") or ""),
        },
        {
            "key": "superego_profile",
            "label": "Superego",
            "value": str(forbidden_moves[0] if forbidden_moves else (conflict.get("self_image_to_protect") or "clear")),
            "meter_label": "Superego Pressure",
            "meter_value": _bounded_float(conflict.get("superego_pressure")),
            "tone": "risk",
            "forbidden_moves": forbidden_moves[:2],
            "self_image_to_protect": str(conflict.get("self_image_to_protect") or ""),
        },
        {
            "key": "ego_profile",
            "label": "Ego Move",
            "value": str(conflict.get("move_style") or "none"),
            "meter_label": "Stability",
            "meter_value": _bounded_float(conflict.get("stability")),
            "tone": "mode",
            "move_family": str(conflict.get("move_family") or ""),
            "dominant_compromise": str(conflict.get("move_rationale") or ""),
        },
        {
            "key": "residue_profile",
            "label": "Residue",
            "value": str(conflict.get("visible_emotion") or "contained"),
            "meter_label": "Residue Intensity",
            "meter_value": _bounded_float(conflict.get("residue_intensity")),
            "tone": "carry",
            "leak_channel": str(conflict.get("leak_channel") or ""),
        },
        {
            "key": "expression_profile",
            "label": "Expression",
            "value": str(expression.get("temperature") or "unknown"),
            "meter_label": "Directness",
            "meter_value": _bounded_float(expression.get("directness")),
            "tone": "block",
            "length": str(expression.get("length") or ""),
            "closure": _bounded_float(expression.get("closure")),
        },
    ]


def _build_expression_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    expression = snapshot.get("expression", {}) or {}
    return [
        {
            "key": "length",
            "label": "Length",
            "value": str(expression.get("length") or "none"),
        },
        {
            "key": "temperature",
            "label": "Temperature",
            "value": str(expression.get("temperature") or "none"),
        },
        {
            "key": "directness",
            "label": "Directness",
            "value": f"{_bounded_float(expression.get('directness')):.2f}",
        },
    ]


def _build_pacing_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    pacing = snapshot.get("pacing", {}) or {}
    return [
        {"key": "relationship_stage", "label": "Stage", "value": str(pacing.get("relationship_stage") or "none")},
        {"key": "commitment_readiness", "label": "Readiness", "value": f"{_bounded_float(pacing.get('commitment_readiness')):.2f}"},
        {"key": "repair_depth", "label": "Repair depth", "value": f"{_bounded_float(pacing.get('repair_depth')):.2f}"},
        {"key": "escalation_allowed", "label": "Escalation", "value": "yes" if pacing.get("escalation_allowed") else "no"},
    ]


def _build_fidelity_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    fidelity = snapshot.get("fidelity", {}) or {}
    rows = [
        {"key": "passed", "label": "Passed", "value": "yes" if fidelity.get("passed") else "no"},
        {"key": "move_fidelity", "label": "Move fidelity", "value": f"{_bounded_float(fidelity.get('move_fidelity')):.2f}"},
        {"key": "warnings", "label": "Warnings", "value": ", ".join(fidelity.get("warnings", []) or []) or "none"},
    ]
    return rows


def _build_conflict_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    conflict = snapshot.get("conflict", {}) or {}
    return [
        {
            "key": "dominant_want",
            "label": "Dominant want",
            "value": str(conflict.get("dominant_want") or "none"),
            "target": str(conflict.get("target") or ""),
        },
        {
            "key": "move_style",
            "label": "Move style",
            "value": str(conflict.get("move_style") or "none"),
            "target": "",
        },
        {
            "key": "residue",
            "label": "Residue",
            "value": str(conflict.get("visible_emotion") or "none"),
            "target": "",
        }
    ]


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


def _appraisal_dimensions(appraisal: dict[str, Any]) -> dict[str, float]:
    target = str(appraisal.get("target_of_tension") or "")
    stakes = str(appraisal.get("stakes") or "low")
    stake_value = {"low": 0.2, "medium": 0.6, "high": 1.0}.get(stakes, 0.0)
    return {
        "confidence": _bounded_float(appraisal.get("confidence")),
        "stakes": _bounded_float(stake_value),
        "closeness_axis": 1.0 if target == "closeness" else 0.0,
        "pride_axis": 1.0 if target == "pride" else 0.0,
        "jealousy_axis": 1.0 if target == "jealousy" else 0.0,
        "ambiguity_axis": 1.0 if target == "ambiguity" else 0.0,
    }
