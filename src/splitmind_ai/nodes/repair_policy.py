"""RepairPolicyNode: derive repair constraints from persona policy and current state."""

from __future__ import annotations

from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.conflict import RepairPolicy

_REPAIR_EVENTS = {"repair_offer", "reassurance", "commitment_request", "exclusive_disclosure"}


class RepairPolicyNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="repair_policy",
        description="Derive repair-specific turn policy from persona style, appraisal, and residue",
        reads=["relational_policy", "relationship_state", "appraisal", "conflict_state", "residue_state"],
        writes=["repair_policy", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=65,
                when={"conflict_state.ego_move.move_family": True},
                when_not={"turn_shaping_policy.primary_frame": True, "repair_policy.repair_mode": True},
                llm_hint="Run after conflict to determine repair-specific acceptance constraints",
            ),
        ],
        is_terminal=False,
        icon="🩹",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        policy = _build_repair_policy(
            relational_policy=inputs.get_slice("relational_policy"),
            relationship_state=inputs.get_slice("relationship_state"),
            appraisal=inputs.get_slice("appraisal"),
            conflict_state=inputs.get_slice("conflict_state"),
            residue_state=inputs.get_slice("residue_state"),
        )
        payload = policy.model_dump(mode="json")
        payload["repair_policy_ms"] = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            repair_policy=payload,
            trace={"repair_policy": payload},
        )


def _build_repair_policy(
    *,
    relational_policy: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    residue_state: dict[str, Any],
) -> RepairPolicy:
    event_type = str(appraisal.get("event_type") or "")
    if event_type not in _REPAIR_EVENTS:
        return RepairPolicy.model_validate({})

    style = str((relational_policy or {}).get("repair_style") or "guarded")
    status_style = str((relational_policy or {}).get("status_maintenance_style") or "medium")
    trust = float((((relationship_state or {}).get("durable") or {}).get("trust", 0.0)) or 0.0)
    opening = float((((relationship_state or {}).get("ephemeral") or {}).get("turn_local_repair_opening", 0.0)) or 0.0)
    residue_load = float((residue_state or {}).get("overall_load", 0.0) or 0.0)
    move_stability = float((((conflict_state or {}).get("ego_move") or {}).get("stability", 0.5)) or 0.5)

    openness = max(0.0, min(1.0, trust * 0.45 + opening * 0.35 + move_stability * 0.2 - residue_load * 0.25))

    if style == "affectionate_inclusion":
        repair_mode = "integrative" if openness >= 0.35 else "receptive"
        warmth_ceiling = min(1.0, 0.72 + trust * 0.18)
        boundary_marker = False
        followup_pull_allowed = True
    elif style == "boundaried_reassurance":
        repair_mode = "receptive" if openness >= 0.28 else "guarded"
        warmth_ceiling = min(1.0, 0.58 + trust * 0.12)
        boundary_marker = True
        followup_pull_allowed = openness >= 0.4
    elif style == "accept_from_above":
        repair_mode = "guarded" if openness < 0.55 else "receptive"
        warmth_ceiling = 0.48
        boundary_marker = True
        followup_pull_allowed = False
    else:
        repair_mode = "guarded" if openness >= 0.18 else "closed"
        warmth_ceiling = 0.36
        boundary_marker = True
        followup_pull_allowed = False

    status_requirement = {
        "high": 0.82,
        "relaxed": 0.22,
        "low": 0.28,
    }.get(status_style, 0.54)
    status_requirement = max(0.0, min(1.0, status_requirement + residue_load * 0.12))

    return RepairPolicy.model_validate({
        "repair_mode": repair_mode,
        "warmth_ceiling": warmth_ceiling,
        "status_preservation_requirement": status_requirement,
        "required_boundary_marker": boundary_marker,
        "followup_pull_allowed": followup_pull_allowed,
    })
