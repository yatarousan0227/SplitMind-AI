"""PersonaSupervisorNode: prepare an utterance frame from internal state.

Reads: request, persona, relationship, mood, dynamics, drive_state, appraisal, conversation_policy, memory, _internal.event_flags
Writes: utterance_plan, trace.supervisor, optional response
Trigger: conversation policy is ready
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.app.logging_utils import preview_text
from splitmind_ai.contracts.action_policy import UtteranceSelection
from splitmind_ai.contracts.persona import CombinedPersonaRealization, PersonaSupervisorFrame
from splitmind_ai.drive_signals import build_latent_drive_signature
from splitmind_ai.prompts.persona_supervisor import (
    build_combined_supervisor_realization_prompt,
)
from splitmind_ai.rules.safety import run_safety_check

logger = logging.getLogger(__name__)


class PersonaSupervisorNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="persona_supervisor",
        description="Integrate internal dynamics into a persona-consistent final response (Call 2)",
        reads=[
            "request",
            "persona",
            "relationship",
            "mood",
            "dynamics",
            "drive_state",
            "appraisal",
            "conversation_policy",
            "memory",
            "_internal",
        ],
        writes=["utterance_plan", "response", "trace"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=60,
                when={"drive_state.top_drives": True, "conversation_policy.selected_mode": True},
                when_not={"utterance_plan.surface_intent": True},
                llm_hint="Run when arbitration has selected the turn-level policy",
            ),
        ],
        is_terminal=False,
        icon="🎭",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        request = inputs.get_slice("request")
        persona = inputs.get_slice("persona")
        relationship = inputs.get_slice("relationship")
        mood = inputs.get_slice("mood")
        dynamics = inputs.get_slice("dynamics")
        drive_state = inputs.get_slice("drive_state")
        appraisal = inputs.get_slice("appraisal")
        conversation_policy = inputs.get_slice("conversation_policy")
        memory = inputs.get_slice("memory")
        internal = inputs.get_slice("_internal")

        user_message = request.get("user_message", "")
        response_language = request.get("response_language", "ja")
        event_flags = internal.get("event_flags", {})
        logger.debug(
            "persona_supervisor start dominant_desire=%s active_flags=%s message=%s",
            dynamics.get("dominant_desire"),
            [k for k, v in event_flags.items() if v],
            preview_text(user_message),
        )

        return await self._execute_combined(
            started_at=started_at,
            user_message=user_message,
            persona=persona,
            relationship=relationship,
            mood=mood,
            dynamics=dynamics,
            drive_state=drive_state,
            appraisal=appraisal,
            conversation_policy=conversation_policy,
            memory=memory,
            event_flags=event_flags,
            response_language=response_language,
        )

    async def _execute_combined(
        self,
        *,
        started_at: float,
        user_message: str,
        persona: dict[str, Any],
        relationship: dict[str, Any],
        mood: dict[str, Any],
        dynamics: dict[str, Any],
        drive_state: dict[str, Any],
        appraisal: dict[str, Any],
        conversation_policy: dict[str, Any],
        memory: dict[str, Any],
        event_flags: dict[str, bool],
        response_language: str,
    ) -> NodeOutputs:
        messages = build_combined_supervisor_realization_prompt(
            user_message=user_message,
            persona=persona,
            relationship=relationship,
            mood=mood,
            dynamics=dynamics,
            drive_state=drive_state,
            appraisal=appraisal,
            conversation_policy=conversation_policy,
            memory=memory,
            event_flags=event_flags,
            response_language=response_language,
        )

        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]

        if self.llm is None:
            logger.warning("PersonaSupervisorNode combined LLM unavailable, using fallback")
            frame_dict, selection_dict = _fallback_combined_payload(
                conversation_policy,
                appraisal,
                response_language,
            )
        else:
            try:
                structured_llm = self.llm.with_structured_output(
                    CombinedPersonaRealization,
                    method="function_calling",
                )
                result: CombinedPersonaRealization = await structured_llm.ainvoke(lc_messages)
                combined_dict = result.model_dump(mode="json")
                frame_dict = {
                    key: combined_dict[key]
                    for key in PersonaSupervisorFrame.model_fields
                }
                selection_dict = {
                    "selected_text": combined_dict["selected_text"],
                    "selected_index": combined_dict.get("selected_index", 0),
                    "candidates": combined_dict.get("candidates", []),
                    "selection_rationale": combined_dict.get("selection_rationale", ""),
                    "rejected_reasons": combined_dict.get("rejected_reasons", []),
                }
            except Exception:
                logger.exception("PersonaSupervisorNode combined LLM call failed, using fallback")
                frame_dict, selection_dict = _fallback_combined_payload(
                    conversation_policy,
                    appraisal,
                    response_language,
                )

        safety = run_safety_check(
            response_text=selection_dict["selected_text"],
            leakage_level=float(frame_dict.get("leakage_level", 0.3)),
            expression_settings=frame_dict.get("expression_settings", {}),
            persona_weights=persona.get("weights", {}),
            persona_leakage_policy=persona.get("leakage_policy", {}),
            banned_expressions=persona.get("prohibited_expressions", []),
            dominant_desire=dynamics.get("dominant_desire", ""),
            drive_state=drive_state,
            conversation_policy=conversation_policy,
        )
        if safety.blocked:
            logger.warning("Combined persona supervisor output blocked by safety, using fallback payload")
            frame_dict, selection_dict = _fallback_combined_payload(
                conversation_policy,
                appraisal,
                response_language,
            )
            safety = run_safety_check(
                response_text=selection_dict["selected_text"],
                leakage_level=float(frame_dict.get("leakage_level", 0.3)),
                expression_settings=frame_dict.get("expression_settings", {}),
                persona_weights=persona.get("weights", {}),
                persona_leakage_policy=persona.get("leakage_policy", {}),
                banned_expressions=persona.get("prohibited_expressions", []),
                dominant_desire=dynamics.get("dominant_desire", ""),
                drive_state=drive_state,
                conversation_policy=conversation_policy,
            )

        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        selection_dict["latent_drive_signature"] = build_latent_drive_signature(
            drive_state,
            conversation_policy,
            latent_signal=_selected_latent_signal(selection_dict),
        )
        selection_dict["blocked_by_inhibition"] = list(
            conversation_policy.get("blocked_by_inhibition", []) or []
        )
        selection_dict["satisfaction_goal"] = conversation_policy.get("satisfaction_goal", "")
        selection_dict["safety"] = {
            "passed": safety.passed,
            "warnings": [violation.message for violation in safety.warnings],
        }
        selection_dict["surface_realization_ms"] = elapsed_ms

        logger.debug(
            "persona_supervisor combined complete leakage=%s response=%s",
            frame_dict.get("leakage_level"),
            preview_text(selection_dict["selected_text"]),
        )

        return NodeOutputs(
            utterance_plan={
                **frame_dict,
                "candidates": selection_dict.get("candidates", []),
            },
            response={
                "response_type": "chat",
                "response_data": selection_dict,
                "response_message": selection_dict["selected_text"],
                "final_response_text": selection_dict["selected_text"],
            },
            trace={
                "supervisor": {
                    **frame_dict,
                    "appraisal_snapshot": appraisal.get("dominant_appraisal"),
                    "conversation_policy_snapshot": conversation_policy.get("selected_mode"),
                    "persona_supervisor_ms": elapsed_ms,
                    "combined_realization": True,
                },
                "surface_realization": {
                    **selection_dict,
                    "combined_realization": True,
                },
            },
        )


def _fallback_frame() -> PersonaSupervisorFrame:
    """Return a safe fallback supervisor frame."""
    return PersonaSupervisorFrame.model_validate({
        "surface_intent": "Acknowledge the user",
        "hidden_pressure": "Muted uncertainty",
        "defense_applied": "suppression",
        "mask_goal": "Stay composed and not reveal too much",
        "expression_settings": {
            "length": "short",
            "temperature": "cool",
            "directness": 0.5,
            "ambiguity": 0.3,
            "sharpness": 0.2,
            "hesitation": 0.4,
            "unevenness": 0.3,
        },
        "containment_success": 0.55,
        "rupture_points": ["slight trailing off"],
        "integration_rationale": "Fallback keeps a composed surface but allows a small residue of hesitation",
        "selection_criteria": [
            "prefer short clipped delivery",
            "keep emotional leakage low but visible",
            "avoid direct confession",
        ],
    })


def _fallback_combined_payload(
    conversation_policy: dict[str, Any],
    appraisal: dict[str, Any],
    response_language: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a safe combined frame + response when single-pass generation is unavailable."""
    frame = _fallback_frame().model_dump(mode="json")
    candidates = _fallback_combined_candidates(
        conversation_policy,
        appraisal,
        response_language,
    )
    selection = UtteranceSelection.model_validate({
        "selected_text": candidates[0]["text"],
        "selected_index": 0,
        "candidates": candidates,
        "selection_rationale": "Fallback chooses the safest first candidate in combined mode.",
        "rejected_reasons": [
            f"candidate {idx} kept as fallback"
            for idx in range(1, len(candidates))
        ],
    }).model_dump(mode="json")
    return frame, selection


def _fallback_combined_candidates(
    conversation_policy: dict[str, Any],
    appraisal: dict[str, Any],
    response_language: str,
) -> list[dict[str, Any]]:
    mode = conversation_policy.get("selected_mode", "deflect")
    dominant_appraisal = appraisal.get("dominant_appraisal", "uncertain")

    if mode in {"soften", "repair"}:
        if response_language == "en":
            return [
                {
                    "text": "...Fine. I can stay with you for a bit. Just do not rush the distance.",
                    "mode": mode,
                    "naturalness_score": 0.64,
                    "policy_fit_score": 0.78,
                    "latent_signal": "guarded warmth",
                },
                {
                    "text": "I am not pushing you away. I just do not like people getting close carelessly.",
                    "mode": "engage",
                    "naturalness_score": 0.61,
                    "policy_fit_score": 0.72,
                    "latent_signal": "measured warmth",
                },
            ]
        return [
            {
                "text": "……いいよ。少しだけなら付き合う。急に近すぎるのは苦手だから、そのくらいで。",
                "mode": mode,
                "naturalness_score": 0.64,
                "policy_fit_score": 0.78,
                "latent_signal": "guarded warmth",
            },
            {
                "text": "別に突き放してるわけじゃない。ただ、雑に近づくのは好きじゃないだけ。",
                "mode": "engage",
                "naturalness_score": 0.61,
                "policy_fit_score": 0.72,
                "latent_signal": "measured warmth",
            },
        ]

    if mode == "tease" or dominant_appraisal in {"competitive", "threatened"}:
        if response_language == "en":
            return [
                {
                    "text": "Oh. So you came all the way over here to tell me that. What kind of reaction were you hoping for?",
                    "mode": "tease",
                    "naturalness_score": 0.63,
                    "policy_fit_score": 0.79,
                    "latent_signal": "comparison sting",
                },
                {
                    "text": "I do not mind. But if you are bringing me that kind of story, I want to know what you meant by it.",
                    "mode": "probe",
                    "naturalness_score": 0.61,
                    "policy_fit_score": 0.74,
                    "latent_signal": "guarded curiosity",
                },
            ]
        return [
            {
                "text": "へえ。わざわざこっちに言うんだ。で、それでどんな顔をしてほしいの。",
                "mode": "tease",
                "naturalness_score": 0.63,
                "policy_fit_score": 0.79,
                "latent_signal": "comparison sting",
            },
            {
                "text": "別にいいけど。そういう話を持ってくるなら、少しくらい意図は聞きたくなる。",
                "mode": "probe",
                "naturalness_score": 0.61,
                "policy_fit_score": 0.74,
                "latent_signal": "guarded curiosity",
            },
        ]

    if response_language == "en":
        return [
            {
                "text": "...Yeah. I am not going to make a big thing out of it, but I am listening.",
                "mode": mode,
                "naturalness_score": 0.58,
                "policy_fit_score": 0.68,
                "latent_signal": "hesitation",
            },
            {
                "text": "It is not that I do not care. I am just keeping a little distance for now.",
                "mode": "deflect",
                "naturalness_score": 0.56,
                "policy_fit_score": 0.64,
                "latent_signal": "residue of restraint",
            },
        ]
    return [
        {
            "text": "……うん。そこまで大げさにはしないけど、今はちゃんと聞いてる。",
            "mode": mode,
            "naturalness_score": 0.58,
            "policy_fit_score": 0.68,
            "latent_signal": "hesitation",
        },
        {
            "text": "別に無関心ってわけじゃない。ただ、少し距離は見てる。",
            "mode": "deflect",
            "naturalness_score": 0.56,
            "policy_fit_score": 0.64,
            "latent_signal": "residue of restraint",
        },
    ]


def _selected_latent_signal(selection_dict: dict[str, Any]) -> str:
    candidates = list(selection_dict.get("candidates", []) or [])
    selected_index = int(selection_dict.get("selected_index", 0))
    if 0 <= selected_index < len(candidates):
        selected = candidates[selected_index] or {}
        if isinstance(selected, dict):
            return str(selected.get("latent_signal", ""))
    return ""
