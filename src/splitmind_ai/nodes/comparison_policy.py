"""ComparisonPolicyNode: derive jealousy/comparison constraints from appraisal and persona policy."""

from __future__ import annotations

from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.conflict import ComparisonPolicy


class ComparisonPolicyNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="comparison_policy",
        description="Derive comparison-specific threat and reclaim constraints",
        reads=["relational_policy", "relationship_state", "appraisal", "conflict_state", "residue_state"],
        writes=["comparison_policy", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=64,
                when={"conflict_state.ego_move.move_family": True},
                when_not={"turn_shaping_policy.primary_frame": True, "trace.comparison_policy": True},
                llm_hint="Run after conflict to determine comparison-specific threat handling",
            ),
        ],
        is_terminal=False,
        icon="🪞",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        policy = _build_comparison_policy(
            relational_policy=inputs.get_slice("relational_policy"),
            relationship_state=inputs.get_slice("relationship_state"),
            appraisal=inputs.get_slice("appraisal"),
            conflict_state=inputs.get_slice("conflict_state"),
            residue_state=inputs.get_slice("residue_state"),
        )
        payload = policy.model_dump(mode="json")
        payload["comparison_policy_ms"] = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            comparison_policy=payload,
            trace={"comparison_policy": payload},
        )


def _build_comparison_policy(
    *,
    relational_policy: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    residue_state: dict[str, Any],
) -> ComparisonPolicy:
    event_mix = dict((appraisal or {}).get("event_mix", {}) or {})
    comparison_frame = str(event_mix.get("comparison_frame") or "none")
    if comparison_frame == "none" and str((appraisal or {}).get("target_of_tension") or "") != "jealousy":
        return ComparisonPolicy.model_validate({})

    style = str((relational_policy or {}).get("comparison_style") or "withhold")
    tension = float((((relationship_state or {}).get("ephemeral") or {}).get("tension", 0.0)) or 0.0)
    attachment_pull = float((((relationship_state or {}).get("durable") or {}).get("attachment_pull", 0.0)) or 0.0)
    residue_load = float((residue_state or {}).get("overall_load", 0.0) or 0.0)
    id_intensity = float((((conflict_state or {}).get("id_impulse") or {}).get("intensity", 0.0)) or 0.0)
    threat = max(0.0, min(1.0, tension * 0.35 + attachment_pull * 0.25 + residue_load * 0.2 + id_intensity * 0.2))

    if style == "playful_reclaim":
        teasing_allowed = True
        direct_reclaim_allowed = threat < 0.72
        self_relevance = min(1.0, 0.56 + attachment_pull * 0.2)
        status_injury = max(0.0, threat - 0.14)
    elif style == "above_the_frame":
        teasing_allowed = threat < 0.52
        direct_reclaim_allowed = False
        self_relevance = min(1.0, 0.62 + attachment_pull * 0.12)
        status_injury = min(1.0, threat + 0.18)
    elif style == "steady_grounding":
        teasing_allowed = False
        direct_reclaim_allowed = False
        self_relevance = min(1.0, 0.44 + attachment_pull * 0.16)
        status_injury = max(0.0, threat - 0.22)
    else:
        teasing_allowed = threat < 0.42
        direct_reclaim_allowed = False
        self_relevance = min(1.0, 0.58 + attachment_pull * 0.18)
        status_injury = min(1.0, threat + 0.12)

    return ComparisonPolicy.model_validate({
        "comparison_threat_level": threat,
        "self_relevance": self_relevance,
        "status_injury": status_injury,
        "teasing_allowed": teasing_allowed,
        "direct_reclaim_allowed": direct_reclaim_allowed,
    })
