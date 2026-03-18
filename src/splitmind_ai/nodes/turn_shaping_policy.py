"""TurnShapingPolicyNode: derive shared mixed-turn shaping constraints."""

from __future__ import annotations

from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.conflict import ComparisonPolicy, RepairPolicy, TurnShapingPolicy

_FRAME_ORDER = (
    "repair_acceptance",
    "affection_receipt",
    "comparison_response",
    "distance_response",
    "boundary_clarification",
)


class TurnShapingPolicyNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="turn_shaping_policy",
        description="Derive shared turn shaping constraints and compatibility policy projections",
        reads=["relational_policy", "relationship_state", "appraisal", "conflict_state", "residue_state"],
        writes=["turn_shaping_policy", "repair_policy", "comparison_policy", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=66,
                when={"conflict_state.ego_move.move_family": True},
                when_not={"turn_shaping_policy.primary_frame": True},
                llm_hint="Run after conflict to derive shared shaping constraints",
            ),
        ],
        is_terminal=False,
        icon="🎚️",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        shaping = _build_turn_shaping_policy(
            relational_policy=inputs.get_slice("relational_policy"),
            relationship_state=inputs.get_slice("relationship_state"),
            appraisal=inputs.get_slice("appraisal"),
            conflict_state=inputs.get_slice("conflict_state"),
            residue_state=inputs.get_slice("residue_state"),
        )
        repair_policy = _project_repair_policy(shaping)
        comparison_policy = _project_comparison_policy(shaping)
        trace_payload = shaping.model_dump(mode="json")
        trace_payload["turn_shaping_policy_ms"] = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            turn_shaping_policy=shaping.model_dump(mode="json"),
            repair_policy=repair_policy.model_dump(mode="json"),
            comparison_policy=comparison_policy.model_dump(mode="json"),
            trace={
                "turn_shaping_policy": trace_payload,
                "repair_policy": repair_policy.model_dump(mode="json"),
                "comparison_policy": comparison_policy.model_dump(mode="json"),
            },
        )


def _build_turn_shaping_policy(
    *,
    relational_policy: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    residue_state: dict[str, Any],
) -> TurnShapingPolicy:
    rel_policy = dict(relational_policy or {})
    rel_act = dict((appraisal or {}).get("relational_act_profile", {}) or {})
    event_mix = dict((appraisal or {}).get("event_mix", {}) or {})
    speaker_intent = dict((appraisal or {}).get("speaker_intent", {}) or {})
    ego_move = dict((conflict_state or {}).get("ego_move", {}) or {})
    durable = dict((relationship_state or {}).get("durable", {}) or {})
    ephemeral = dict((relationship_state or {}).get("ephemeral", {}) or {})

    frame_scores = {
        "repair_acceptance": max(
            _f(rel_act.get("repair_bid")),
            _f(rel_act.get("reassurance")) * 0.85,
            0.78 if speaker_intent.get("user_repair_bid") else 0.0,
            0.62 if str(event_mix.get("primary_event") or "") == "repair_offer" else 0.0,
        ),
        "affection_receipt": max(
            _f(rel_act.get("affection")),
            _f(rel_act.get("commitment")) * 0.58,
            _f(rel_act.get("priority_restore")) * 0.55,
        ),
        "comparison_response": max(
            _f(rel_act.get("comparison")),
            _f(event_mix.get("priority_signal_strength")) * 0.72,
            0.66 if str(event_mix.get("comparison_frame") or "") not in {"", "none"} else 0.0,
        ),
        "distance_response": max(
            _f(rel_act.get("distancing")),
            _f(event_mix.get("distance_signal_strength")),
            0.85 if speaker_intent.get("user_distance_request") else 0.0,
        ),
        "boundary_clarification": 0.28 + _f((conflict_state.get("expression_envelope") or {}).get("closure")) * 0.25,
    }

    move_family = str(ego_move.get("move_family") or "")
    if move_family in frame_scores:
        frame_scores[move_family] = max(frame_scores[move_family], 0.7)

    ordered_frames = [
        frame
        for frame, score in sorted(frame_scores.items(), key=lambda item: (item[1], -_FRAME_ORDER.index(item[0])), reverse=True)
        if score >= 0.18
    ]
    primary_frame = ordered_frames[0] if ordered_frames else "boundary_clarification"
    secondary_frame = next((frame for frame in ordered_frames[1:] if frame != primary_frame), "")
    mixed_turn = len([frame for frame in ordered_frames[:3] if frame_scores.get(frame, 0.0) >= 0.42]) >= 2

    repair_style = str(rel_policy.get("repair_style") or "")
    comparison_style = str(rel_policy.get("comparison_style") or "")
    status_style = str(rel_policy.get("status_maintenance_style") or "medium")
    warmth_style = str(rel_policy.get("warmth_release_style") or "")
    trust = _f(durable.get("trust"))
    intimacy = _f(durable.get("intimacy"))
    tension = _f(ephemeral.get("tension"))
    residue_load = _f((residue_state or {}).get("overall_load"))

    preserved_counterforce = _select_counterforce(
        primary_frame=primary_frame,
        secondary_frame=secondary_frame,
        repair_style=repair_style,
        comparison_style=comparison_style,
        status_style=status_style,
        warmth_style=warmth_style,
        mixed_turn=mixed_turn,
        tension=tension,
        residue_load=residue_load,
    )

    warmth_floor = _clamp(
        0.18
        + _f(rel_act.get("affection")) * 0.22
        + _f(rel_act.get("reassurance")) * 0.14
        + trust * 0.08
    )
    warmth_ceiling = _clamp(
        0.32
        + trust * 0.16
        + intimacy * 0.10
        + _warmth_style_bonus(warmth_style)
        - _counterforce_cooling(preserved_counterforce)
        - residue_load * 0.10
    )
    if warmth_ceiling < warmth_floor:
        warmth_ceiling = warmth_floor

    reciprocity_ceiling = _clamp(
        warmth_ceiling
        - 0.12
        - (0.12 if preserved_counterforce in {"status", "distance", "sting"} else 0.0)
        + (0.10 if preserved_counterforce == "pace" else 0.0)
    )
    disclosure_ceiling = _clamp(
        0.28
        + trust * 0.22
        + intimacy * 0.12
        - (0.12 if preserved_counterforce in {"status", "distance"} else 0.0)
        - (0.08 if preserved_counterforce == "sting" else 0.0)
    )
    followup_pull_allowed = (
        preserved_counterforce not in {"distance", "status"}
        and warmth_ceiling >= 0.52
        and frame_scores.get("affection_receipt", 0.0) >= 0.35
    )

    required_surface_markers = {
        "acknowledge_bid": primary_frame in {"repair_acceptance", "affection_receipt", "comparison_response", "distance_response"},
        "holdback_marker": preserved_counterforce in {"status", "sting", "distance", "uncertainty", "pace"},
        "boundary_marker": preserved_counterforce in {"sting", "distance"} or secondary_frame == "boundary_clarification",
        "status_marker": preserved_counterforce == "status" or status_style == "high",
        "pace_marker": preserved_counterforce == "pace" or mixed_turn,
    }
    forbidden_collapses = {
        "gratitude_only": primary_frame == "repair_acceptance",
        "instant_reciprocity": preserved_counterforce in {"status", "sting", "distance", "pace"} or reciprocity_ceiling < 0.75,
        "generic_reassurance": primary_frame == "repair_acceptance" or secondary_frame == "repair_acceptance",
        "generic_agreement": primary_frame == "comparison_response" or secondary_frame == "comparison_response",
        "full_repair_reset": frame_scores.get("repair_acceptance", 0.0) >= 0.45 and preserved_counterforce != "none",
    }

    return TurnShapingPolicy.model_validate({
        "primary_frame": primary_frame,
        "secondary_frame": secondary_frame,
        "preserved_counterforce": preserved_counterforce,
        "warmth_floor": round(warmth_floor, 4),
        "warmth_ceiling": round(warmth_ceiling, 4),
        "reciprocity_ceiling": round(reciprocity_ceiling, 4),
        "disclosure_ceiling": round(disclosure_ceiling, 4),
        "required_surface_markers": required_surface_markers,
        "forbidden_collapses": forbidden_collapses,
        "followup_pull_allowed": followup_pull_allowed,
        "surface_guidance_mode": "none",
    })


def _project_repair_policy(shaping: TurnShapingPolicy) -> RepairPolicy:
    frames = {shaping.primary_frame, shaping.secondary_frame}
    if "repair_acceptance" not in frames:
        return RepairPolicy.model_validate({})

    if shaping.preserved_counterforce in {"status", "sting", "distance"}:
        repair_mode = "guarded"
    elif shaping.preserved_counterforce == "pace":
        repair_mode = "receptive"
    else:
        repair_mode = "integrative" if shaping.warmth_ceiling >= 0.72 else "receptive"

    return RepairPolicy.model_validate({
        "repair_mode": repair_mode,
        "warmth_ceiling": shaping.warmth_ceiling,
        "status_preservation_requirement": 0.82 if shaping.preserved_counterforce == "status" else (0.34 if shaping.preserved_counterforce == "pace" else 0.58),
        "required_boundary_marker": bool(shaping.required_surface_markers.boundary_marker or shaping.required_surface_markers.holdback_marker),
        "followup_pull_allowed": shaping.followup_pull_allowed,
    })


def _project_comparison_policy(shaping: TurnShapingPolicy) -> ComparisonPolicy:
    frames = {shaping.primary_frame, shaping.secondary_frame}
    if "comparison_response" not in frames:
        return ComparisonPolicy.model_validate({})

    threat = 0.72 if shaping.preserved_counterforce in {"sting", "status"} else (0.48 if shaping.preserved_counterforce == "pace" else 0.4)
    return ComparisonPolicy.model_validate({
        "comparison_threat_level": threat,
        "self_relevance": 0.68 if shaping.preserved_counterforce in {"status", "sting"} else 0.52,
        "status_injury": 0.76 if shaping.preserved_counterforce == "status" else (0.58 if shaping.preserved_counterforce == "sting" else 0.28),
        "teasing_allowed": shaping.preserved_counterforce not in {"distance", "status"},
        "direct_reclaim_allowed": shaping.preserved_counterforce == "pace" and shaping.reciprocity_ceiling >= 0.55,
    })


def _select_counterforce(
    *,
    primary_frame: str,
    secondary_frame: str,
    repair_style: str,
    comparison_style: str,
    status_style: str,
    warmth_style: str,
    mixed_turn: bool,
    tension: float,
    residue_load: float,
) -> str:
    if primary_frame == "distance_response":
        return "distance"
    if comparison_style == "stung_then_withhold" or repair_style == "cool_accept_with_edge":
        return "sting" if max(tension, residue_load) >= 0.32 else "distance"
    if status_style == "high" or repair_style == "accept_from_above":
        return "status"
    if repair_style == "boundaried_reassurance":
        return "pace"
    if repair_style == "affectionate_inclusion":
        if secondary_frame in {"repair_acceptance", "comparison_response"} or mixed_turn:
            return "pace"
        return "none" if warmth_style == "quick_rewarding" and tension < 0.18 else "pace"
    if secondary_frame == "comparison_response":
        return "uncertainty"
    if primary_frame == "comparison_response":
        return "sting"
    if mixed_turn:
        return "pace"
    return "none"


def _warmth_style_bonus(style: str) -> float:
    return {
        "quick_rewarding": 0.28,
        "steady": 0.14,
        "selective_elegant": 0.08,
        "selective_slow": 0.02,
    }.get(style, 0.06)


def _counterforce_cooling(counterforce: str) -> float:
    return {
        "status": 0.14,
        "sting": 0.18,
        "distance": 0.16,
        "pace": 0.06,
        "uncertainty": 0.10,
        "none": 0.0,
    }.get(counterforce, 0.08)


def _f(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
