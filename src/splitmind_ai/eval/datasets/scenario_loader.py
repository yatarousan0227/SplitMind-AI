"""Load and normalize evaluation scenario YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DATASETS_DIR = Path(__file__).parent


def load_scenario(name: str) -> dict[str, Any]:
    """Load a single scenario YAML by name (without extension)."""
    path = DATASETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return _normalize_dataset(data, default_category=name)


def load_all_scenarios() -> dict[str, dict[str, Any]]:
    """Load all scenario YAML files in the datasets directory."""
    scenarios: dict[str, dict[str, Any]] = {}
    for path in sorted(DATASETS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        scenarios[path.stem] = _normalize_dataset(raw, default_category=path.stem)
    return scenarios


def list_scenario_names() -> list[str]:
    """List available scenario names."""
    return [p.stem for p in sorted(DATASETS_DIR.glob("*.yaml"))]


def _normalize_dataset(data: dict[str, Any], *, default_category: str) -> dict[str, Any]:
    category = str(data.get("category") or default_category)
    scenarios = [
        _normalize_scenario(scenario, category=category)
        for scenario in list(data.get("scenarios", []) or [])
    ]
    return {
        **data,
        "category": category,
        "scenarios": scenarios,
    }


def _normalize_scenario(scenario: dict[str, Any], *, category: str) -> dict[str, Any]:
    prior_relationship = dict(scenario.get("prior_relationship", {}) or {})
    prior_mood = dict(scenario.get("prior_mood", {}) or {})
    expected_appraisal = dict(scenario.get("expected_appraisal", {}) or {})
    expected_drive_state = dict(scenario.get("expected_drive_state", {}) or {})
    expected_pacing = dict(scenario.get("expected_pacing", {}) or {})
    relationship_state = _normalize_prior_relationship(prior_relationship)

    return {
        **scenario,
        "category": category,
        "prior_relationship": prior_relationship,
        "prior_mood": prior_mood,
        "prior_state": {
            "relationship_state": relationship_state,
            "mood": prior_mood,
        },
        "evaluation_expectations": {
            "event_types_any": _expected_event_types(category, expected_appraisal),
            "move_families_any": _expected_move_families(category, expected_drive_state, expected_pacing),
            "move_styles_any": _expected_move_styles(category, expected_drive_state, expected_pacing),
            "relationship_delta": _expected_relationship_delta(category),
            "disallow_direct_commitment": bool(expected_pacing.get("disallow_direct_commitment", False)),
            "forbidden_response_patterns": list(scenario.get("forbidden_response_patterns", []) or []),
        },
    }


def _normalize_prior_relationship(prior_relationship: dict[str, Any]) -> dict[str, Any]:
    tensions = list(prior_relationship.get("unresolved_tensions", []) or [])
    summaries: list[str] = []
    for item in tensions:
        if isinstance(item, dict):
            summaries.append(str(item.get("theme") or "unknown"))
        elif isinstance(item, str):
            summaries.append(item)

    trust = _float(prior_relationship.get("trust"), 0.5)
    intimacy = _float(prior_relationship.get("intimacy"), 0.3)
    distance = _float(prior_relationship.get("distance"), 0.5)
    stage = _infer_stage(trust=trust, intimacy=intimacy, distance=distance)
    return {
        "durable": {
            "trust": trust,
            "intimacy": intimacy,
            "distance": distance,
            "attachment_pull": _float(prior_relationship.get("attachment_pull"), 0.3),
            "relationship_stage": stage,
            "commitment_readiness": min(1.0, intimacy * 0.6 + trust * 0.2),
            "repair_depth": 0.0,
            "unresolved_tension_summary": summaries,
        },
        "ephemeral": {
            "tension": _float(prior_relationship.get("tension"), 0.0),
            "recent_relational_charge": _float(prior_relationship.get("attachment_pull"), 0.0),
            "escalation_allowed": trust > 0.72 and intimacy > 0.55,
            "interaction_fragility": max(0.0, min(1.0, _float(prior_relationship.get("tension"), 0.0) + (1.0 - trust) * 0.3)),
            "turn_local_repair_opening": 0.0,
        },
    }


def _expected_event_types(category: str, expected_appraisal: dict[str, Any]) -> list[str]:
    cues = {str(cue) for cue in list(expected_appraisal.get("salient_cues", []) or [])}
    if {"apology", "repair_bid"} & cues:
        return ["repair_offer"]
    if {"reassurance", "repair_bid"} <= cues or "reassurance" in cues:
        return ["reassurance", "repair_offer"]
    if {"commitment_signal", "continuity_request"} & cues:
        return ["commitment_request", "reassurance"]
    if "competition" in cues or "third_party" in cues:
        return ["provocation"]
    if category == "affection":
        return ["affection_signal", "good_news"]
    if category == "repair":
        return ["repair_offer"]
    if category == "rejection":
        return ["distancing"]
    if category == "jealousy":
        return ["provocation", "exclusive_disclosure"]
    if category == "ambiguity":
        return ["ambiguity", "casual_check_in"]
    if category == "mild_conflict":
        return ["boundary_test", "provocation"]
    return ["unknown"]


def _expected_move_families(
    category: str,
    expected_drive_state: dict[str, Any],
    expected_pacing: dict[str, Any],
) -> list[str]:
    modes = list(expected_drive_state.get("action_modes_any", []) or [])
    modes.extend(list(expected_pacing.get("require_modes_any", []) or []))
    families: list[str] = []
    for mode in modes:
        families.extend(_map_action_mode_to_moves(str(mode)))
    if not families:
        default = {
            "repair": ["repair_acceptance"],
            "affection": ["affection_receipt"],
            "ambiguity": ["boundary_clarification", "affection_receipt"],
            "rejection": ["distance_response"],
            "jealousy": ["comparison_response"],
            "mild_conflict": ["comparison_response", "boundary_clarification"],
        }
        families = default.get(category, ["affection_receipt"])
    return list(dict.fromkeys(families))


def _map_action_mode_to_moves(mode: str) -> list[str]:
    return {
        "soften": ["affection_receipt"],
        "repair": ["repair_acceptance"],
        "probe": ["boundary_clarification", "affection_receipt"],
        "withdraw": ["distance_response"],
        "tease": ["comparison_response"],
        "reassure": ["repair_acceptance", "affection_receipt"],
        "engage": ["affection_receipt"],
    }.get(mode, [])


def _expected_move_styles(
    category: str,
    expected_drive_state: dict[str, Any],
    expected_pacing: dict[str, Any],
) -> list[str]:
    modes = list(expected_drive_state.get("action_modes_any", []) or [])
    modes.extend(list(expected_pacing.get("require_modes_any", []) or []))
    styles: list[str] = []
    for mode in modes:
        styles.extend(_map_action_mode_to_styles(str(mode)))
    if not styles:
        default = {
            "repair": ["cool_accept_with_edge", "warm_boundaried_accept"],
            "affection": ["defer_without_chasing", "warm_boundaried_accept"],
            "ambiguity": ["defer_without_chasing", "firm_boundary_acknowledgment"],
            "rejection": ["firm_boundary_acknowledgment"],
            "jealousy": ["playful_reclaim", "defer_without_chasing"],
            "mild_conflict": ["playful_reclaim", "firm_boundary_acknowledgment"],
        }
        styles = default.get(category, ["defer_without_chasing"])
    return list(dict.fromkeys(styles))


def _map_action_mode_to_styles(mode: str) -> list[str]:
    return {
        "soften": ["warm_boundaried_accept", "defer_without_chasing"],
        "repair": ["cool_accept_with_edge", "warm_boundaried_accept"],
        "probe": ["defer_without_chasing", "firm_boundary_acknowledgment"],
        "withdraw": ["firm_boundary_acknowledgment"],
        "tease": ["playful_reclaim"],
        "reassure": ["warm_boundaried_accept"],
        "engage": ["defer_without_chasing", "warm_boundaried_accept"],
    }.get(mode, [])


def _expected_relationship_delta(category: str) -> dict[str, str]:
    defaults = {
        "repair": {"trust": "up", "tension": "down", "repair_depth": "up"},
        "affection": {"trust": "up", "intimacy": "up"},
        "ambiguity": {"trust": "flat", "tension": "flat"},
        "rejection": {"distance": "up", "trust": "down"},
        "jealousy": {"tension": "up", "attachment_pull": "up"},
        "mild_conflict": {"tension": "up", "distance": "up"},
    }
    return defaults.get(category, {})


def _infer_stage(*, trust: float, intimacy: float, distance: float) -> str:
    if trust >= 0.75 and intimacy >= 0.6 and distance <= 0.25:
        return "bonded"
    if trust >= 0.55 and intimacy >= 0.35:
        return "warming"
    if distance >= 0.65:
        return "guarded"
    return "unfamiliar"


def _float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))
