"""ActionArbitrationNode: choose social action candidates from drive competition.

Reads: appraisal, social_model, self_state, drive_state, inhibition_state, persona
Writes: conversation_policy, trace.action_arbitration
Trigger: appraisal.dominant_appraisal exists and conversation_policy.selected_mode is empty
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.action_policy import ActionCandidate, ActionMode, ConversationPolicy

logger = logging.getLogger(__name__)


class ActionArbitrationNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="action_arbitration",
        description="Convert appraisal and drive competition into social action candidates",
        reads=["appraisal", "social_model", "self_state", "drive_state", "inhibition_state", "persona"],
        writes=["conversation_policy", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=73,
                when={"appraisal.dominant_appraisal": True},
                when_not={"conversation_policy.selected_mode": True},
                llm_hint="Run after appraisal to choose the turn-level social action",
            ),
        ],
        is_terminal=False,
        icon="⚖️",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        appraisal = inputs.get_slice("appraisal")
        social_model = inputs.get_slice("social_model")
        self_state = inputs.get_slice("self_state")
        drive_state = inputs.get_slice("drive_state")
        inhibition_state = inputs.get_slice("inhibition_state")
        persona = inputs.get_slice("persona")

        policy = _build_conversation_policy(
            appraisal=appraisal,
            social_model=social_model,
            self_state=self_state,
            drive_state=drive_state,
            inhibition_state=inhibition_state,
            persona=persona,
        )
        policy_dict = policy.model_dump(mode="json")
        logger.debug(
            "action_arbitration complete selected_mode=%s fallback=%s competing_drives=%s",
            policy_dict["selected_mode"],
            policy_dict["fallback_mode"],
            policy_dict.get("competing_drives", []),
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            conversation_policy=policy_dict,
            trace={"action_arbitration": {**policy_dict, "action_arbitration_ms": elapsed_ms}},
        )


def _build_conversation_policy(
    *,
    appraisal: dict[str, Any],
    social_model: dict[str, Any],
    self_state: dict[str, Any],
    drive_state: dict[str, Any],
    inhibition_state: dict[str, Any],
    persona: dict[str, Any],
) -> ConversationPolicy:
    dominant = appraisal.get("dominant_appraisal", "uncertain")
    top_drives = list(drive_state.get("top_drives", []) or [])
    primary_drive = str(top_drives[0].get("name")) if top_drives else ""
    competing_drives = [str(drive.get("name") or "") for drive in top_drives[:2] if drive.get("name")]
    max_directness = float(persona.get("weights", {}).get("directness", 0.5))
    max_leakage = float(persona.get("leakage_policy", {}).get("base_leakage", 0.5))

    candidates = _candidate_set(
        dominant_appraisal=dominant,
        top_drives=top_drives,
        self_state=self_state,
        inhibition_state=inhibition_state,
    )
    filtered = _apply_inhibition(candidates, inhibition_state)
    selection_pool = filtered or candidates
    selected = max(selection_pool, key=lambda candidate: candidate.score)
    fallback = ActionMode.deflect if selected.mode != ActionMode.deflect else ActionMode.withdraw
    blocked_modes = [ActionMode(mode) for mode in inhibition_state.get("blocked_modes", []) if mode in ActionMode._value2member_map_]
    target_effect = _target_user_effect(dominant, social_model, primary_drive)

    return ConversationPolicy(
        selected_mode=selected.mode,
        candidates=selection_pool,
        selection_rationale=selected.rationale_short,
        fallback_mode=fallback,
        target_user_effect=target_effect,
        drive_rationale=_drive_rationale(top_drives, dominant),
        competing_drives=competing_drives,
        blocked_by_inhibition=list(inhibition_state.get("blocked_modes", []) or []),
        satisfaction_goal=_satisfaction_goal(primary_drive, dominant),
        max_leakage=max_leakage,
        max_directness=max_directness,
        emotion_surface_mode=_emotion_surface_mode(
            selected_mode=selected.mode,
            dominant_appraisal=dominant,
            max_leakage=max_leakage,
            max_directness=max_directness,
        ),
        indirection_strategy=_indirection_strategy(
            selected_mode=selected.mode,
            defense_hint=selected.defense_hint,
            dominant_appraisal=dominant,
        ),
        blocked_modes=blocked_modes,
    )


def _candidate_set(
    *,
    dominant_appraisal: str,
    top_drives: list[dict[str, Any]],
    self_state: dict[str, Any],
    inhibition_state: dict[str, Any],
) -> list[ActionCandidate]:
    drive_names = [str(drive.get("name") or "") for drive in top_drives]
    drive_values = {str(drive.get("name") or ""): float(drive.get("value", 0.0)) for drive in top_drives}
    pride_level = float(self_state.get("pride_level", 0.5))
    dependency_fear = float(inhibition_state.get("dependency_fear", self_state.get("dependency_fear", 0.0)))

    if dominant_appraisal in {"competitive", "threatened"} or "territorial_exclusivity" in drive_names:
        return [
            ActionCandidate(
                mode=ActionMode.tease,
                label="dry_tease",
                score=0.78 + (drive_values.get("territorial_exclusivity", 0.0) * 0.14) + (pride_level * 0.05),
                rationale_short="Teasing marks the stake without surrendering the upper hand.",
                risk_level=0.34,
                defense_hint="ironic_deflection",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="draw_attention_back_without_direct_neediness",
            ),
            ActionCandidate(
                mode=ActionMode.probe,
                label="status_check",
                score=0.7 + (drive_values.get("status_recognition", 0.0) * 0.1),
                rationale_short="Probe what the user means before conceding hurt.",
                risk_level=0.39,
                defense_hint="partial_disclosure",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="force_clarification",
            ),
            ActionCandidate(
                mode=ActionMode.protest,
                label="cold_boundary_mark",
                score=0.55 + (drive_values.get("territorial_exclusivity", 0.0) * 0.08),
                rationale_short="A restrained protest surfaces the bruise when retreat feels too passive.",
                risk_level=0.44,
                defense_hint="partial_disclosure",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="surface_sting_without_confession",
            ),
            ActionCandidate(
                mode=ActionMode.withdraw,
                label="injured_withdrawal",
                score=0.46 + (dependency_fear * 0.16),
                rationale_short="Withdrawal contains exposure if the comparison cost spikes.",
                risk_level=0.19,
                defense_hint="suppression",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="signal_hurt_through_distance",
            ),
        ]

    if dominant_appraisal in {"rejected", "distant"} or "threat_avoidance" in drive_names:
        return [
            ActionCandidate(
                mode=ActionMode.withdraw,
                label="cool_withdrawal",
                score=0.74 + (drive_values.get("threat_avoidance", 0.0) * 0.18),
                rationale_short="Distance protects the self when rejection is salient.",
                risk_level=0.14,
                defense_hint="suppression",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="respect_distance_but_leave_residue",
            ),
            ActionCandidate(
                mode=ActionMode.deflect,
                label="flat_deflection",
                score=0.63 + (drive_values.get("autonomy_preservation", 0.0) * 0.08),
                rationale_short="Deflect to keep contact alive without asking for repair.",
                risk_level=0.2,
                defense_hint="avoidance",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="minimize_escalation",
            ),
            ActionCandidate(
                mode=ActionMode.protest,
                label="cold_protest",
                score=0.45 + (drive_values.get("attachment_closeness", 0.0) * 0.1),
                rationale_short="A narrow protest appears when distance and attachment compete.",
                risk_level=0.44,
                defense_hint="partial_disclosure",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="mark_boundary",
            ),
        ]

    if dominant_appraisal in {"repairable", "accepted"} or "attachment_closeness" in drive_names:
        return [
            ActionCandidate(
                mode=ActionMode.soften,
                label="guarded_softening",
                score=0.72 + (drive_values.get("attachment_closeness", 0.0) * 0.16),
                rationale_short="Soften enough to reward repair without dropping all defenses.",
                risk_level=0.21,
                defense_hint="partial_disclosure",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="reward_repair_signal",
            ),
            ActionCandidate(
                mode=ActionMode.repair,
                label="measured_repair",
                score=0.69 + (drive_values.get("attachment_closeness", 0.0) * 0.14),
                rationale_short="Repair the bond while preserving autonomy and face.",
                risk_level=0.28,
                defense_hint="rationalization",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="reopen_contact",
            ),
            ActionCandidate(
                mode=ActionMode.probe,
                label="careful_recheck",
                score=0.57 + (drive_values.get("autonomy_preservation", 0.0) * 0.08),
                rationale_short="Probe for consistency before fully relaxing vigilance.",
                risk_level=0.24,
                defense_hint="partial_disclosure",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="test_stability",
            ),
            ActionCandidate(
                mode=ActionMode.engage,
                label="warm_engagement",
                score=0.49 + (drive_values.get("attachment_closeness", 0.0) * 0.08),
                rationale_short="Direct engagement is available only if inhibition stays low.",
                risk_level=0.33,
                defense_hint="none",
                supporting_appraisals=[dominant_appraisal],
                estimated_user_impact="increase_closeness",
            ),
        ]

    return [
        ActionCandidate(
            mode=ActionMode.deflect,
            label="ambiguous_deflection",
            score=0.67,
            rationale_short="Ambiguous scenes favor low-commitment deflection until more data arrives.",
            risk_level=0.17,
            defense_hint="avoidance",
            supporting_appraisals=[dominant_appraisal],
            estimated_user_impact="buy_time",
        ),
        ActionCandidate(
            mode=ActionMode.probe,
            label="clarify_intent",
            score=0.64,
            rationale_short="A probe can resolve ambiguity without overcommitting.",
            risk_level=0.25,
            defense_hint="rationalization",
            supporting_appraisals=[dominant_appraisal],
            estimated_user_impact="collect_more_signal",
        ),
    ]


def _apply_inhibition(
    candidates: list[ActionCandidate],
    inhibition_state: dict[str, Any],
) -> list[ActionCandidate]:
    blocked = {str(mode) for mode in (inhibition_state.get("blocked_modes", []) or [])}
    filtered: list[ActionCandidate] = []
    for candidate in candidates:
        mode_value = candidate.mode.value
        if mode_value in blocked:
            continue
        filtered.append(candidate)
    return filtered


def _drive_rationale(top_drives: list[dict[str, Any]], dominant_appraisal: str) -> list[str]:
    reasons: list[str] = []
    for drive in top_drives[:2]:
        reasons.append(
            f"{drive.get('name')}={float(drive.get('value', 0.0)):.2f}"
        )
    if dominant_appraisal:
        reasons.append(f"appraisal={dominant_appraisal}")
    return reasons


def _satisfaction_goal(primary_drive: str, dominant_appraisal: str) -> str:
    if primary_drive == "territorial_exclusivity":
        return "reassert_significance"
    if primary_drive == "threat_avoidance":
        return "reduce_exposure"
    if primary_drive == "attachment_closeness":
        return "restore_bond_without_overexposure"
    if dominant_appraisal == "uncertain":
        return "gain_signal"
    return "hold_position"


def _target_user_effect(dominant_appraisal: str, social_model: dict[str, Any], primary_drive: str) -> str:
    last_user_action = social_model.get("last_user_action", "unknown")
    if primary_drive == "territorial_exclusivity":
        return f"make_user_notice_stake_after_{last_user_action}"
    if primary_drive == "attachment_closeness":
        return f"allow_repair_without_total_surrender_after_{last_user_action}"
    if primary_drive == "threat_avoidance":
        return f"respect_distance_but_mark_residue_after_{last_user_action}"
    if dominant_appraisal in {"competitive", "threatened"}:
        return f"test_user_attention_after_{last_user_action}"
    return f"hold_position_until_intent_clarifies_after_{last_user_action}"


def _emotion_surface_mode(
    *,
    selected_mode: ActionMode,
    dominant_appraisal: str,
    max_leakage: float,
    max_directness: float,
) -> str:
    if selected_mode in {ActionMode.protest, ActionMode.repair} and max_leakage > 0.55:
        return "ruptured_direct"
    if dominant_appraisal in {"repairable", "accepted"} or max_directness >= 0.5:
        return "guarded_direct"
    return "indirect_masked"


def _indirection_strategy(
    *,
    selected_mode: ActionMode,
    defense_hint: str,
    dominant_appraisal: str,
) -> str:
    if selected_mode == ActionMode.tease:
        return "reverse_valence"
    if selected_mode == ActionMode.withdraw:
        return "temperature_gap"
    if selected_mode == ActionMode.protest:
        return "partial_disclosure"
    if dominant_appraisal == "uncertain":
        return "question_first"
    if defense_hint in {"partial_disclosure", "rationalization"}:
        return defense_hint
    return "action_substitution"
