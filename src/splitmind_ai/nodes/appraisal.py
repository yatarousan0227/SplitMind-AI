"""AppraisalNode: convert cues and dynamics into subjective social meaning.

Reads: request, relationship, mood, dynamics, drive_state, appraisal.social_cues, working_memory
Writes: appraisal, social_model, self_state, trace.appraisal
Trigger: appraisal.social_cues exists and appraisal.dominant_appraisal is empty
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.appraisal import (
    AppraisalBundle,
    AppraisalDimension,
    AppraisalLabel,
    AppraisalState,
    SelfState,
    SocialCueType,
    SocialIntentHypothesis,
    SocialModelState,
)

logger = logging.getLogger(__name__)


class AppraisalNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="appraisal",
        description="Transform social cues into appraisal, social model, and self-state",
        reads=["request", "relationship", "mood", "dynamics", "drive_state", "appraisal", "working_memory"],
        writes=["appraisal", "social_model", "self_state", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=74,
                when={"appraisal.social_cues": True},
                when_not={"appraisal.dominant_appraisal": True},
                llm_hint="Run after social cue detection to estimate subjective meaning",
            ),
        ],
        is_terminal=False,
        icon="🧭",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        request = inputs.get_slice("request")
        relationship = inputs.get_slice("relationship")
        mood = inputs.get_slice("mood")
        dynamics = inputs.get_slice("dynamics")
        drive_state = inputs.get_slice("drive_state")
        appraisal_slice = inputs.get_slice("appraisal")
        working_memory = inputs.get_slice("working_memory")

        social_cues = appraisal_slice.get("social_cues", [])
        bundle = _build_appraisal_bundle(
            user_message=request.get("user_message", ""),
            relationship=relationship,
            mood=mood,
            dynamics=dynamics,
            drive_state=drive_state,
            social_cues=social_cues,
            working_memory=working_memory,
        )
        bundle_dict = bundle.model_dump(mode="json")
        logger.debug(
            "appraisal complete dominant_appraisal=%s confidence=%.2f",
            bundle_dict["appraisal"]["dominant_appraisal"],
            bundle_dict["appraisal"]["dominant_appraisal_confidence"],
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            appraisal={
                "social_cues": bundle_dict["social_cues"],
                **bundle_dict["appraisal"],
            },
            social_model=bundle_dict["social_model"],
            self_state=bundle_dict["self_state"],
            trace={"appraisal": {**bundle_dict, "appraisal_ms": elapsed_ms}},
        )


def _build_appraisal_bundle(
    *,
    user_message: str,
    relationship: dict[str, Any],
    mood: dict[str, Any],
    dynamics: dict[str, Any],
    drive_state: dict[str, Any],
    social_cues: list[dict[str, Any]],
    working_memory: dict[str, Any],
) -> AppraisalBundle:
    cue_types = [SocialCueType(cue["cue_type"]) for cue in social_cues]
    top_drives = list(drive_state.get("top_drives", []) or [])
    top_drive_names = [str(drive.get("name") or "") for drive in top_drives]
    dominant_desire = top_drive_names[0] if top_drive_names else dynamics.get("dominant_desire", "")
    active_themes = working_memory.get("active_themes", [])

    acceptance = _dimension(
        score=0.76 if SocialCueType.acceptance in cue_types else 0.18,
        confidence=0.8,
        cues=cue_types,
        trend="rising" if SocialCueType.acceptance in cue_types else "stable",
    )
    rejection = _dimension(
        score=0.82 if SocialCueType.rejection in cue_types else 0.15,
        confidence=0.82,
        cues=cue_types,
        trend="rising" if SocialCueType.rejection in cue_types else "stable",
    )
    competition = _dimension(
        score=0.84 if SocialCueType.competition in cue_types else 0.12,
        confidence=0.87,
        cues=cue_types,
        trend="rising" if SocialCueType.competition in cue_types else "stable",
    )
    perceived_distance = _dimension(
        score=0.74 if SocialCueType.distancing in cue_types else relationship.get("distance", 0.3),
        confidence=0.76,
        cues=cue_types,
        trend="rising" if SocialCueType.distancing in cue_types else "stable",
    )
    ambiguity = _dimension(
        score=0.58 if SocialCueType.ambiguity in cue_types else 0.18,
        confidence=0.63,
        cues=cue_types,
        trend="stable",
    )
    face_threat = _dimension(
        score=_face_threat_score(dominant_desire, cue_types),
        confidence=0.81,
        cues=cue_types,
        trend="rising" if dominant_desire in {"territorial_exclusivity", "threat_avoidance"} else "stable",
    )
    attachment_activation = _dimension(
        score=_attachment_activation_score(dominant_desire, cue_types, relationship),
        confidence=0.84,
        cues=cue_types,
        trend="rising" if dominant_desire else "stable",
    )
    repair_opportunity = _dimension(
        score=0.79 if SocialCueType.repair_bid in cue_types else 0.14,
        confidence=0.77,
        cues=cue_types,
        trend="rising" if SocialCueType.repair_bid in cue_types else "stable",
    )

    appraisal_values = {
        AppraisalLabel.accepted: acceptance.score,
        AppraisalLabel.rejected: rejection.score,
        AppraisalLabel.competitive: competition.score,
        AppraisalLabel.distant: perceived_distance.score,
        AppraisalLabel.uncertain: ambiguity.score,
        AppraisalLabel.threatened: face_threat.score,
        AppraisalLabel.repairable: repair_opportunity.score,
    }
    dominant_appraisal = max(appraisal_values, key=appraisal_values.get)
    dominant_confidence = appraisal_values[dominant_appraisal]

    active_wounds = _derive_active_wounds(dominant_desire, cue_types, active_themes)
    social_model = SocialModelState(
        user_current_intent_hypotheses=_intent_hypotheses(cue_types),
        user_attachment_guess="engaged" if relationship.get("attachment_pull", 0.0) > 0.35 else "uncertain",
        user_sensitivity_guess=active_wounds[:3],
        confidence=0.62,
        recent_prediction_errors=[],
        last_user_action=_last_user_action(cue_types),
    )
    self_state = SelfState(
        threatened_self_image=_threatened_self_images(dominant_desire, cue_types),
        pride_level=0.72 if dominant_appraisal in {AppraisalLabel.competitive, AppraisalLabel.threatened} else 0.48,
        shame_activation=0.36 if dominant_appraisal == AppraisalLabel.threatened else 0.12,
        dependency_fear=0.66 if dominant_desire in {"territorial_exclusivity", "threat_avoidance"} else 0.28,
        desire_for_closeness=0.74 if "attachment_closeness" in top_drive_names else 0.41,
        urge_to_test_user=0.71 if dominant_appraisal in {AppraisalLabel.competitive, AppraisalLabel.threatened} else 0.22,
        active_defenses=[dynamics.get("defense_output", {}).get("selected_mechanism", "")] if dynamics.get("defense_output") else [],
    )
    appraisal = AppraisalState(
        perceived_acceptance=acceptance,
        perceived_rejection=rejection,
        perceived_competition=competition,
        perceived_distance=perceived_distance,
        ambiguity=ambiguity,
        face_threat=face_threat,
        attachment_activation=attachment_activation,
        repair_opportunity=repair_opportunity,
        dominant_appraisal=dominant_appraisal,
        dominant_appraisal_confidence=dominant_confidence,
        active_wounds=active_wounds,
        triggered_drives=top_drive_names[:3],
        targeted_wounds=active_wounds[:3],
        self_image_threats=_threatened_self_images(dominant_desire, cue_types),
        summary_short=_summary_short(user_message, dominant_appraisal, cue_types),
    )
    return AppraisalBundle(
        social_cues=social_cues,
        appraisal=appraisal,
        social_model=social_model,
        self_state=self_state,
        source_turn_id=str(working_memory.get("current_episode_summary") or user_message[:40]),
    )


def _dimension(
    *,
    score: float,
    confidence: float,
    cues: list[SocialCueType],
    trend: str,
) -> AppraisalDimension:
    return AppraisalDimension(
        score=min(1.0, max(0.0, score)),
        confidence=min(1.0, max(0.0, confidence)),
        rationale_short="rule_based_appraisal",
        trend=trend,
        driver_cues=cues[:3],
    )


def _face_threat_score(dominant_desire: str, cue_types: list[SocialCueType]) -> float:
    base = 0.18
    if SocialCueType.competition in cue_types:
        base += 0.42
    if SocialCueType.rejection in cue_types:
        base += 0.32
    if dominant_desire in {"territorial_exclusivity", "threat_avoidance"}:
        base += 0.08
    return base


def _attachment_activation_score(
    dominant_desire: str,
    cue_types: list[SocialCueType],
    relationship: dict[str, Any],
) -> float:
    base = relationship.get("attachment_pull", 0.3)
    if SocialCueType.competition in cue_types or SocialCueType.rejection in cue_types:
        base += 0.28
    if dominant_desire in {"attachment_closeness", "curiosity_approach"}:
        base += 0.18
    return base


def _derive_active_wounds(
    dominant_desire: str,
    cue_types: list[SocialCueType],
    active_themes: list[str],
) -> list[str]:
    wounds = list(active_themes)
    if dominant_desire in {"territorial_exclusivity", "status_recognition"}:
        wounds.append("special_to_user")
    if SocialCueType.rejection in cue_types:
        wounds.append("unwanted")
    if SocialCueType.repair_bid in cue_types:
        wounds.append("uncertain_bond")
    return list(dict.fromkeys(wounds))[:5]


def _intent_hypotheses(cue_types: list[SocialCueType]) -> list[SocialIntentHypothesis]:
    if SocialCueType.competition in cue_types:
        return [
            SocialIntentHypothesis(label="seek_comparison_reaction", confidence=0.76, supporting_cues=[SocialCueType.competition]),
            SocialIntentHypothesis(label="share_social_update", confidence=0.58, supporting_cues=[SocialCueType.competition]),
        ]
    if SocialCueType.repair_bid in cue_types:
        return [SocialIntentHypothesis(label="repair_relationship", confidence=0.82, supporting_cues=[SocialCueType.repair_bid])]
    if SocialCueType.rejection in cue_types:
        return [SocialIntentHypothesis(label="set_distance", confidence=0.79, supporting_cues=[SocialCueType.rejection, SocialCueType.distancing])]
    return [SocialIntentHypothesis(label="signal_ambiguity", confidence=0.42, supporting_cues=[SocialCueType.ambiguity])]


def _last_user_action(cue_types: list[SocialCueType]) -> str:
    if SocialCueType.competition in cue_types:
        return "comparison"
    if SocialCueType.repair_bid in cue_types:
        return "repair"
    if SocialCueType.rejection in cue_types:
        return "distance"
    if SocialCueType.acceptance in cue_types:
        return "reassure"
    return "ambiguous"


def _threatened_self_images(dominant_desire: str, cue_types: list[SocialCueType]) -> list[str]:
    images: list[str] = []
    if dominant_desire in {"territorial_exclusivity", "status_recognition"}:
        images.append("special_to_user")
    if SocialCueType.rejection in cue_types:
        images.append("easy_to_leave")
    if SocialCueType.repair_bid in cue_types:
        images.append("hard_to_trust")
    return images or ["composed_self"]


def _summary_short(
    user_message: str,
    dominant_appraisal: AppraisalLabel,
    cue_types: list[SocialCueType],
) -> str:
    cue_label = cue_types[0].value if cue_types else "ambiguity"
    return f"{cue_label} cue in '{user_message[:40]}' produced {dominant_appraisal.value} appraisal"
