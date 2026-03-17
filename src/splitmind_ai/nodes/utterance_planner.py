"""UtterancePlannerNode: derive 2-3 plausible candidate blueprints.

Reads: utterance_plan, conversation_policy, appraisal
Writes: utterance_plan, trace.utterance_planner
Trigger: utterance_plan.surface_intent exists and utterance_plan.candidates is empty
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.persona import UtteranceBlueprint

logger = logging.getLogger(__name__)


class UtterancePlannerNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="utterance_planner",
        description="Build 2-3 utterance blueprints from the supervisor frame and action policy",
        reads=["utterance_plan", "conversation_policy", "appraisal"],
        writes=["utterance_plan", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=59,
                when={"utterance_plan.surface_intent": True},
                when_not={"utterance_plan.candidates": True},
                llm_hint="Run after supervisor framing to propose multiple plausible utterances",
            ),
        ],
        is_terminal=False,
        icon="📝",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        frame = dict(inputs.get_slice("utterance_plan"))
        policy = inputs.get_slice("conversation_policy")
        appraisal = inputs.get_slice("appraisal")

        candidates = _build_blueprints(frame, policy, appraisal)
        candidate_dicts = [candidate.model_dump(mode="json") for candidate in candidates]
        logger.debug(
            "utterance_planner complete candidate_labels=%s",
            [candidate["label"] for candidate in candidate_dicts],
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            utterance_plan={"candidates": candidate_dicts},
            trace={"utterance_planner": {"candidates": candidate_dicts, "utterance_planner_ms": elapsed_ms}},
        )


def _build_blueprints(
    frame: dict[str, Any],
    policy: dict[str, Any],
    appraisal: dict[str, Any],
) -> list[UtteranceBlueprint]:
    mode = policy.get("selected_mode", "deflect")
    dominant_appraisal = appraisal.get("dominant_appraisal", "uncertain")
    hidden_pressure = frame.get("hidden_pressure", "")
    length_target = (frame.get("expression_settings", {}) or {}).get("length", "short")
    must_include = _must_include_terms(appraisal)

    if mode == "tease":
        return [
            UtteranceBlueprint(
                label="dry_tease",
                mode=mode,
                opening_style=_length_aware_opening(
                    "short dry acknowledgment",
                    length_target,
                    allow_follow_up=False,
                ),
                interpersonal_move="lightly sting and test the user's awareness",
                latent_signal=hidden_pressure or "comparison sting",
                must_include=must_include,
                avoid=_length_aware_avoid(length_target, ["direct confession", "therapy tone"]),
            ),
            UtteranceBlueprint(
                label="cool_probe",
                mode=mode,
                opening_style=_length_aware_opening(
                    "cool question after clipped acknowledgment",
                    length_target,
                ),
                interpersonal_move="probe the user's priorities",
                latent_signal="wanting to know where you stand",
                must_include=must_include,
                avoid=_length_aware_avoid(length_target, ["overexplaining"]),
            ),
            UtteranceBlueprint(
                label="injured_pullback",
                mode="withdraw",
                opening_style=_length_aware_opening(
                    "flat acknowledgment then small retreat",
                    length_target,
                ),
                interpersonal_move="mark the sting by stepping back",
                latent_signal="hurt tucked behind composure",
                must_include=must_include[:1],
                avoid=_length_aware_avoid(length_target, ["sweet reassurance"]),
            ),
        ]

    if mode in {"soften", "repair"}:
        return [
            UtteranceBlueprint(
                label="guarded_acceptance",
                mode=mode,
                opening_style=_length_aware_opening(
                    "guarded but not hostile",
                    length_target,
                ),
                interpersonal_move="accept the repair without dropping pride",
                latent_signal=hidden_pressure or "care still held back",
                must_include=must_include,
                avoid=_length_aware_avoid(length_target, ["instant forgiveness", "grand declaration"]),
            ),
            UtteranceBlueprint(
                label="measured_warmth",
                mode="engage",
                opening_style=_length_aware_opening(
                    "small warmth after hesitation",
                    length_target,
                ),
                interpersonal_move="reopen connection carefully",
                latent_signal="relief leaking through restraint",
                must_include=must_include[:1],
                avoid=_length_aware_avoid(length_target, ["too much sweetness"]),
            ),
        ]

    if mode in {"withdraw", "deflect", "protest"}:
        return [
            UtteranceBlueprint(
                label="cool_withdrawal",
                mode=mode,
                opening_style=_length_aware_opening(
                    "brief flat acknowledgment",
                    length_target,
                    allow_follow_up=False,
                ),
                interpersonal_move="leave distance without overt complaint",
                latent_signal=hidden_pressure or "residue of hurt",
                must_include=must_include[:1],
                avoid=_length_aware_avoid(length_target, ["repair invitation"]),
            ),
            UtteranceBlueprint(
                label="restrained_protest",
                mode="protest",
                opening_style=_length_aware_opening(
                    "cool line with a small edge",
                    length_target,
                ),
                interpersonal_move="mark the injury while preserving self-respect",
                latent_signal="boundary setting",
                must_include=must_include,
                avoid=_length_aware_avoid(length_target, ["begging"]),
            ),
        ]

    return [
        UtteranceBlueprint(
            label="ambiguous_hold",
            mode=mode,
            opening_style=_length_aware_opening(
                "noncommittal acknowledgment",
                length_target,
                allow_follow_up=False,
            ),
            interpersonal_move="buy time while holding the interaction",
            latent_signal=hidden_pressure or dominant_appraisal,
            must_include=must_include[:1],
            avoid=_length_aware_avoid(length_target, ["too much certainty"]),
        ),
        UtteranceBlueprint(
            label="quiet_probe",
            mode="probe",
            opening_style=_length_aware_opening(
                "short acknowledgment followed by a light probe",
                length_target,
            ),
            interpersonal_move="collect more signal",
            latent_signal="uncertain stake",
            must_include=must_include[:1],
            avoid=_length_aware_avoid(length_target, ["long explanation"]),
        ),
    ]


def _length_aware_opening(
    base_style: str,
    length_target: str,
    *,
    allow_follow_up: bool = True,
) -> str:
    """Describe how much room the realization step has to elaborate."""
    if length_target == "long":
        if allow_follow_up:
            return f"{base_style}; allow a fuller reply with 2-3 follow-up beats"
        return f"{base_style}; stay concise in opening but allow later expansion"
    if length_target == "medium":
        if allow_follow_up:
            return f"{base_style}; allow one extra follow-up sentence"
        return f"{base_style}; keep it compact but not one-line flat"
    return base_style


def _length_aware_avoid(length_target: str, avoid: list[str]) -> list[str]:
    """Prevent medium/long targets from collapsing into one-liners."""
    extras = [] if length_target == "short" else ["one-line retreat", "too terse to carry the scene"]
    return [*avoid, *extras]


def _must_include_terms(appraisal: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    social_cues = appraisal.get("social_cues", [])
    for cue in social_cues:
        evidence = cue.get("evidence", "")
        for token in ("他の", "別", "見習", "忙しい", "また今度", "ごめん", "一番"):
            if token in evidence and token not in terms:
                terms.append(token)
    return terms[:2]
