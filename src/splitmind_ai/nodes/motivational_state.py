"""MotivationalStateNode: persist and rank drive hypotheses across turns.

Reads: dynamics, drive_state, relationship, mood, persona, _internal.event_flags
Writes: drive_state, inhibition_state, dynamics, trace.motivational_state
Trigger: dynamics.id_output exists and drive_state.top_drives is empty
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

logger = logging.getLogger(__name__)


class MotivationalStateNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="motivational_state",
        description="Fuse current drive hypotheses with carryover motivational state",
        reads=["dynamics", "drive_state", "relationship", "mood", "persona", "_internal"],
        writes=["drive_state", "inhibition_state", "dynamics", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=76,
                when={"dynamics.id_output": True},
                when_not={"drive_state.top_drives": True},
                llm_hint="Run after internal dynamics to construct persistent drive state",
            ),
        ],
        is_terminal=False,
        icon="🔥",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        dynamics = inputs.get_slice("dynamics")
        prior_drive_state = inputs.get_slice("drive_state")
        relationship = inputs.get_slice("relationship")
        mood = inputs.get_slice("mood")
        persona = inputs.get_slice("persona")
        internal = inputs.get_slice("_internal")

        event_flags = internal.get("event_flags", {}) or {}
        drive_state, inhibition_state, dynamics_patch = _build_motivational_state(
            dynamics=dynamics,
            prior_drive_state=prior_drive_state,
            relationship=relationship,
            mood=mood,
            persona=persona,
            event_flags=event_flags,
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)

        logger.debug(
            "motivational_state complete top_drives=%s blocked_modes=%s",
            [drive["name"] for drive in drive_state.get("top_drives", [])],
            inhibition_state.get("blocked_modes", []),
        )

        return NodeOutputs(
            drive_state=drive_state,
            inhibition_state=inhibition_state,
            dynamics=dynamics_patch,
            trace={
                "motivational_state": {
                    "drive_state": drive_state,
                    "inhibition_state": inhibition_state,
                    "motivational_state_ms": elapsed_ms,
                }
            },
        )


def _build_motivational_state(
    *,
    dynamics: dict[str, Any],
    prior_drive_state: dict[str, Any],
    relationship: dict[str, Any],
    mood: dict[str, Any],
    persona: dict[str, Any],
    event_flags: dict[str, bool],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    id_output = dynamics.get("id_output", {}) or {}
    axes = list(id_output.get("drive_axes", []) or [])
    prior_vector = _as_float_map(prior_drive_state.get("drive_vector"))
    prior_frustration = _as_float_map(prior_drive_state.get("frustration_vector"))
    prior_satiation = _as_float_map(prior_drive_state.get("satiation_vector"))
    prior_suppression = _as_float_map(prior_drive_state.get("suppression_vector"))
    prior_carryover = _as_float_map(prior_drive_state.get("carryover_vector"))
    prior_targets = dict(prior_drive_state.get("drive_targets", {}) or {})

    drive_vector: dict[str, float] = {}
    frustration_vector: dict[str, float] = {}
    satiation_vector: dict[str, float] = {}
    suppression_vector: dict[str, float] = {}
    carryover_vector: dict[str, float] = {}
    drive_targets: dict[str, str] = {}
    ranked_axes: list[dict[str, Any]] = []

    for axis in axes:
        name = str(axis.get("name") or "")
        if not name:
            continue
        current_value = _clamp(axis.get("value"))
        previous_value = prior_vector.get(name, 0.0)
        carry_boost = prior_carryover.get(name, 0.0) * 0.45
        blended_value = _clamp(max(current_value, (previous_value * 0.52) + carry_boost))

        frustration = _clamp(
            (prior_frustration.get(name, 0.0) * 0.55)
            + max(0.0, blended_value - 0.48) * 0.42
            + _event_frustration_delta(name, event_flags)
        )
        satiation = _clamp(
            (prior_satiation.get(name, 0.0) * 0.42)
            + _event_satiation_delta(name, event_flags)
        )
        suppression = _clamp(
            max(
                _clamp(axis.get("suppression_load")),
                prior_suppression.get(name, 0.0) * 0.55,
                _clamp(id_output.get("suppression_risk")) * 0.45,
            )
        )
        carryover = _clamp(max(frustration * 0.7, blended_value * 0.35, prior_carryover.get(name, 0.0) * 0.45))
        target = str(axis.get("target") or prior_targets.get(name) or _default_target(name))

        drive_vector[name] = blended_value
        frustration_vector[name] = frustration
        satiation_vector[name] = satiation
        suppression_vector[name] = suppression
        carryover_vector[name] = carryover
        drive_targets[name] = target
        ranked_axes.append({
            "name": name,
            "value": blended_value,
            "target": target,
            "urgency": _clamp(axis.get("urgency", blended_value)),
            "frustration": frustration,
            "satiation": satiation,
            "carryover": carryover,
            "suppression_load": suppression,
        })

    if not ranked_axes:
        ranked_axes = [{
            "name": "curiosity_approach",
            "value": 0.26,
            "target": "conversation",
            "urgency": 0.18,
            "frustration": 0.0,
            "satiation": 0.0,
            "carryover": 0.12,
            "suppression_load": 0.08,
        }]
        drive_vector = {"curiosity_approach": 0.26}
        frustration_vector = {"curiosity_approach": 0.0}
        satiation_vector = {"curiosity_approach": 0.0}
        suppression_vector = {"curiosity_approach": 0.08}
        carryover_vector = {"curiosity_approach": 0.12}
        drive_targets = {"curiosity_approach": "conversation"}

    ranked_axes.sort(key=lambda item: item["value"], reverse=True)
    top_drives = ranked_axes[:3]
    top_drive_names = [drive["name"] for drive in top_drives]
    last_satisfied = _last_satisfied_drive(event_flags, top_drive_names)
    last_blocked = _last_blocked_drive(event_flags, top_drive_names)

    drive_state = {
        "drive_vector": drive_vector,
        "top_drives": top_drives,
        "drive_targets": drive_targets,
        "frustration_vector": frustration_vector,
        "satiation_vector": satiation_vector,
        "suppression_vector": suppression_vector,
        "carryover_vector": carryover_vector,
        "last_satisfied_drive": last_satisfied,
        "last_blocked_drive": last_blocked,
        "summary_short": ", ".join(f"{drive['name']}={drive['value']:.2f}" for drive in top_drives),
    }

    inhibition_state = _build_inhibition_state(
        dynamics=dynamics,
        top_drives=top_drives,
        relationship=relationship,
        mood=mood,
        persona=persona,
    )
    dominant_legacy = top_drives[0]["name"] if top_drives else ""
    dynamics_patch = {
        "id_output": id_output,
        "ego_output": dynamics.get("ego_output", {}),
        "superego_output": dynamics.get("superego_output", {}),
        "defense_output": dynamics.get("defense_output", {}),
        "drive_axes": top_drives,
        "target_lock": _clamp(id_output.get("target_lock")),
        "suppression_risk": _clamp(id_output.get("suppression_risk")),
        "dominant_desire": dominant_legacy,
        "affective_pressure": _clamp(id_output.get("affective_pressure_score")),
    }
    return drive_state, inhibition_state, dynamics_patch


def _build_inhibition_state(
    *,
    dynamics: dict[str, Any],
    top_drives: list[dict[str, Any]],
    relationship: dict[str, Any],
    mood: dict[str, Any],
    persona: dict[str, Any],
) -> dict[str, Any]:
    superego = dynamics.get("superego_output", {}) or {}
    defense = dynamics.get("defense_output", {}) or {}
    defense_biases = persona.get("defense_biases", {}) or {}
    role_pressure = _clamp(max(
        superego.get("shame_or_guilt_pressure"),
        1.0 - _clamp(superego.get("role_alignment_score", 0.0)),
        _clamp(superego.get("ideal_self_gap", 0.0)),
    ))
    face_preservation = _clamp(max(
        relationship.get("tension", 0.0) * 0.7,
        mood.get("irritation", 0.0) * 0.55,
        top_drives[0]["suppression_load"] if top_drives else 0.0,
    ))
    dependency_fear = _clamp(max(
        relationship.get("distance", 0.0) * 0.45,
        next((drive["value"] for drive in top_drives if drive["name"] == "threat_avoidance"), 0.0) * 0.9,
        next((drive["suppression_load"] for drive in top_drives if drive["name"] == "attachment_closeness"), 0.0) * 0.85,
    ))
    pride_level = _clamp(max(
        next((drive["value"] for drive in top_drives if drive["name"] in {"territorial_exclusivity", "status_recognition"}), 0.0),
        face_preservation * 0.85,
    ))
    blocked_modes = _blocked_modes(top_drives, dependency_fear, role_pressure)
    allowed_modes = [mode for mode in _candidate_mode_order(top_drives) if mode not in blocked_modes][:4]

    preferred_defenses = [str(defense.get("selected_mechanism") or "")]
    preferred_defenses.extend(
        name
        for name, _score in sorted(defense_biases.items(), key=lambda item: item[1], reverse=True)
        if name not in preferred_defenses
    )
    preferred_defenses = [name for name in preferred_defenses if name][:3]

    blocked_drives = [
        drive["name"]
        for drive in top_drives
        if drive.get("suppression_load", 0.0) >= 0.45
    ]

    return {
        "role_pressure": role_pressure,
        "face_preservation": face_preservation,
        "dependency_fear": dependency_fear,
        "pride_level": pride_level,
        "allowed_modes": allowed_modes,
        "blocked_modes": blocked_modes,
        "preferred_defenses": preferred_defenses,
        "blocked_drives": blocked_drives,
    }


def _blocked_modes(top_drives: list[dict[str, Any]], dependency_fear: float, role_pressure: float) -> list[str]:
    blocked: list[str] = []
    drive_names = {drive["name"] for drive in top_drives}
    if dependency_fear > 0.55 or "threat_avoidance" in drive_names:
        blocked.append("engage")
    if role_pressure > 0.45 or "autonomy_preservation" in drive_names:
        blocked.append("reassure")
    if any(drive.get("suppression_load", 0.0) >= 0.4 for drive in top_drives):
        blocked.append("full_disclosure")
    return blocked


def _candidate_mode_order(top_drives: list[dict[str, Any]]) -> list[str]:
    drive_names = [drive["name"] for drive in top_drives]
    if "territorial_exclusivity" in drive_names:
        return ["tease", "probe", "protest", "withdraw", "deflect"]
    if "threat_avoidance" in drive_names:
        return ["withdraw", "deflect", "probe", "protest"]
    if "attachment_closeness" in drive_names:
        return ["soften", "repair", "engage", "probe"]
    return ["deflect", "probe", "engage"]


def _event_frustration_delta(name: str, event_flags: dict[str, bool]) -> float:
    if event_flags.get("rejection_signal") and name in {"attachment_closeness", "territorial_exclusivity"}:
        return 0.18
    if event_flags.get("user_praised_third_party") and name in {"territorial_exclusivity", "status_recognition"}:
        return 0.14
    return 0.0


def _event_satiation_delta(name: str, event_flags: dict[str, bool]) -> float:
    if event_flags.get("reassurance_received") and name == "attachment_closeness":
        return 0.42
    if event_flags.get("repair_attempt") and name in {"attachment_closeness", "territorial_exclusivity"}:
        return 0.28
    return 0.0


def _last_satisfied_drive(event_flags: dict[str, bool], top_drive_names: list[str]) -> str | None:
    if event_flags.get("reassurance_received") and "attachment_closeness" in top_drive_names:
        return "attachment_closeness"
    if event_flags.get("repair_attempt") and top_drive_names:
        return top_drive_names[0]
    return None


def _last_blocked_drive(event_flags: dict[str, bool], top_drive_names: list[str]) -> str | None:
    if event_flags.get("rejection_signal") and "attachment_closeness" in top_drive_names:
        return "attachment_closeness"
    if event_flags.get("user_praised_third_party") and "territorial_exclusivity" in top_drive_names:
        return "territorial_exclusivity"
    return None


def _default_target(name: str) -> str:
    if name in {"attachment_closeness", "territorial_exclusivity", "status_recognition"}:
        return "user"
    if name == "threat_avoidance":
        return "threat_source"
    return "conversation"


def _as_float_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, item in value.items():
        result[str(key)] = _clamp(item)
    return result


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))
