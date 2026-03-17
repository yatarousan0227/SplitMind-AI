"""SocialCueNode: derive interpersonal cue candidates from the current turn.

Reads: request, drive_state, _internal.event_flags
Writes: appraisal.social_cues, trace.social_cue
Trigger: drive_state.top_drives exists and appraisal.social_cues is empty
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.contracts.appraisal import SocialCue, SocialCueType

logger = logging.getLogger(__name__)


class SocialCueNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="social_cue",
        description="Detect salient interpersonal cues before appraisal",
        reads=["request", "drive_state", "_internal"],
        writes=["appraisal", "trace"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=75,
                when={"drive_state.top_drives": True},
                when_not={"appraisal.social_cues": True},
                llm_hint="Run after internal dynamics to derive social cue candidates",
            ),
        ],
        is_terminal=False,
        icon="🛰️",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        request = inputs.get_slice("request")
        internal = inputs.get_slice("_internal")
        user_message = request.get("user_message", "")
        event_flags = internal.get("event_flags", {})

        cues = _detect_social_cues(user_message, event_flags)
        cue_dicts = [cue.model_dump(mode="json") for cue in cues]
        logger.debug(
            "social_cue complete cue_types=%s",
            [cue["cue_type"] for cue in cue_dicts],
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        return NodeOutputs(
            appraisal={"social_cues": cue_dicts},
            trace={"social_cue": {"social_cues": cue_dicts, "social_cue_ms": elapsed_ms}},
        )


def _detect_social_cues(user_message: str, event_flags: dict[str, bool]) -> list[SocialCue]:
    message = user_message or ""
    cues: list[SocialCue] = []

    def add(cue_type: SocialCueType, evidence: str, intensity: float, confidence: float) -> None:
        cues.append(SocialCue(
            cue_type=cue_type,
            evidence=evidence,
            intensity=intensity,
            confidence=confidence,
        ))

    if event_flags.get("user_praised_third_party") or any(
        phrase in message for phrase in ("他の人", "あの子", "別の友達", "見習")
    ):
        add(SocialCueType.competition, message[:120], 0.82, 0.88)

    if event_flags.get("rejection_signal") or any(
        phrase in message for phrase in ("忙しい", "また今度", "話したくない", "用事")
    ):
        add(SocialCueType.rejection, message[:120], 0.78, 0.83)
        add(SocialCueType.distancing, message[:120], 0.72, 0.8)

    if event_flags.get("repair_attempt") or any(
        phrase in message for phrase in ("ごめん", "言い過ぎ", "やっぱり", "一番大事")
    ):
        add(SocialCueType.repair_bid, message[:120], 0.74, 0.86)

    if event_flags.get("reassurance_received") or any(
        phrase in message for phrase in ("一番", "大事", "話すのが一番", "あなたでいい")
    ):
        add(SocialCueType.acceptance, message[:120], 0.7, 0.8)

    if any(phrase in message for phrase in ("大丈夫", "心配", "無理しない")):
        add(SocialCueType.care_signal, message[:120], 0.58, 0.7)

    if not cues:
        add(SocialCueType.ambiguity, message[:120], 0.35, 0.55)

    return cues
