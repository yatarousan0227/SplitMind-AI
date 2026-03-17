"""SurfaceRealizationNode: realize/select the final response from candidate blueprints.

Reads: request, persona, relationship, mood, dynamics, appraisal, conversation_policy, utterance_plan, memory
Writes: response, trace.surface_realization
Trigger: utterance_plan.candidates exists and response.final_response_text is empty
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.app.logging_utils import preview_text
from splitmind_ai.contracts.action_policy import UtteranceSelection
from splitmind_ai.drive_signals import build_latent_drive_signature
from splitmind_ai.prompts.persona_supervisor import build_surface_realization_prompt
from splitmind_ai.rules.safety import run_safety_check

logger = logging.getLogger(__name__)


class SurfaceRealizationNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="surface_realization",
        description="Write/select the final response from multiple candidate blueprints",
        reads=[
            "request",
            "persona",
            "relationship",
            "mood",
            "dynamics",
            "drive_state",
            "appraisal",
            "conversation_policy",
            "utterance_plan",
            "memory",
        ],
        writes=["response", "trace"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=58,
                when={"utterance_plan.candidates": True},
                when_not={"response.final_response_text": True},
                llm_hint="Run after utterance planner to realize and select a final response",
            ),
        ],
        is_terminal=False,
        icon="🗣️",
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
        utterance_plan = inputs.get_slice("utterance_plan")
        memory = inputs.get_slice("memory")

        user_message = request.get("user_message", "")
        response_language = request.get("response_language", "ja")
        logger.debug(
            "surface_realization start candidate_count=%s message=%s",
            len(utterance_plan.get("candidates", [])),
            preview_text(user_message),
        )

        messages = build_surface_realization_prompt(
            user_message=user_message,
            persona=persona,
            relationship=relationship,
            mood=mood,
            dynamics=dynamics,
            drive_state=drive_state,
            appraisal=appraisal,
            conversation_policy=conversation_policy,
            utterance_plan=utterance_plan,
            memory=memory,
            response_language=response_language,
        )
        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]

        if self.llm is None:
            logger.warning("SurfaceRealizationNode LLM unavailable, using fallback")
            result = _fallback_selection(utterance_plan, conversation_policy, response_language)
        else:
            try:
                structured_llm = self.llm.with_structured_output(
                    UtteranceSelection,
                    method="function_calling",
                )
                result: UtteranceSelection = await structured_llm.ainvoke(lc_messages)
            except Exception:
                logger.exception("SurfaceRealizationNode LLM call failed, using fallback")
                result = _fallback_selection(utterance_plan, conversation_policy, response_language)

        safety = run_safety_check(
            response_text=result.selected_text,
            leakage_level=float(utterance_plan.get("leakage_level", 0.3)),
            expression_settings=utterance_plan.get("expression_settings", {}),
            persona_weights=persona.get("weights", {}),
            persona_leakage_policy=persona.get("leakage_policy", {}),
            banned_expressions=persona.get("prohibited_expressions", []),
            dominant_desire=dynamics.get("dominant_desire", ""),
            drive_state=drive_state,
            conversation_policy=conversation_policy,
        )
        if safety.blocked:
            logger.warning("Surface realization blocked by safety, using fallback selection")
            result = _fallback_selection(utterance_plan, conversation_policy, response_language)
            safety = run_safety_check(
                response_text=result.selected_text,
                leakage_level=float(utterance_plan.get("leakage_level", 0.3)),
                expression_settings=utterance_plan.get("expression_settings", {}),
                persona_weights=persona.get("weights", {}),
                persona_leakage_policy=persona.get("leakage_policy", {}),
                banned_expressions=persona.get("prohibited_expressions", []),
                dominant_desire=dynamics.get("dominant_desire", ""),
                drive_state=drive_state,
                conversation_policy=conversation_policy,
            )

        selection_dict = result.model_dump(mode="json")
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
        selection_dict["surface_realization_ms"] = round((perf_counter() - started_at) * 1000, 2)
        logger.debug(
            "surface_realization complete selected_index=%s response=%s",
            selection_dict.get("selected_index"),
            preview_text(result.selected_text),
        )
        return NodeOutputs(
            response={
                "response_type": "chat",
                "response_data": selection_dict,
                "response_message": result.selected_text,
                "final_response_text": result.selected_text,
            },
            trace={"surface_realization": selection_dict},
        )


def _fallback_selection(
    utterance_plan: dict[str, Any],
    conversation_policy: dict[str, Any],
    response_language: str,
) -> UtteranceSelection:
    candidates = utterance_plan.get("candidates", [])
    realized = []
    selected_index = 0
    for idx, blueprint in enumerate(candidates[:3]):
        realized.append({
            "text": _realize_blueprint_text(blueprint, response_language),
            "mode": blueprint.get("mode", conversation_policy.get("selected_mode", "deflect")),
            "naturalness_score": 0.62 - (idx * 0.03),
            "policy_fit_score": 0.76 - (idx * 0.04),
            "latent_signal": blueprint.get("latent_signal", ""),
        })
    if not realized:
        realized = [{
            "text": "...Yeah." if response_language == "en" else "...うん。",
            "mode": conversation_policy.get("selected_mode", "deflect"),
            "naturalness_score": 0.5,
            "policy_fit_score": 0.5,
            "latent_signal": "hesitation",
        }]
    return UtteranceSelection.model_validate({
        "selected_text": realized[selected_index]["text"],
        "selected_index": selected_index,
        "candidates": realized,
        "selection_rationale": "Fallback chooses the first plausible candidate.",
        "rejected_reasons": [
            f"candidate {idx} kept as fallback"
            for idx in range(1, len(realized))
        ],
    })


def _realize_blueprint_text(blueprint: dict[str, Any], response_language: str) -> str:
    opening_style = blueprint.get("opening_style", "")
    latent_signal = blueprint.get("latent_signal", "")
    must_include = blueprint.get("must_include", [])
    if response_language == "en":
        if "question" in opening_style or blueprint.get("mode") == "probe":
            anchor = must_include[0] if must_include else "that"
            return f"Huh. So it was {anchor}. ...What are you trying to tell me with that?"
        if blueprint.get("mode") in {"withdraw", "deflect"}:
            anchor = must_include[0] if must_include else "that"
            return f"I see. If it is {anchor}, then fine."
        anchor = must_include[0] if must_include else "that"
        suffix = " ...Not that I care that much." if latent_signal else "."
        return f"Oh, so it was {anchor}{suffix}"
    if "question" in opening_style or blueprint.get("mode") == "probe":
        anchor = must_include[0] if must_include else "それ"
        return f"へえ、{anchor}なんだ。……で、そこまで言うってことは何かあるの？"
    if blueprint.get("mode") in {"withdraw", "deflect"}:
        anchor = must_include[0] if must_include else "そう"
        return f"ふーん。{anchor}なら別にいいけど。"
    anchor = must_include[0] if must_include else "そう"
    suffix = "……まあ、別に気にしてないけど。" if latent_signal else "。"
    return f"へえ、{anchor}なんだ{suffix}"


def _selected_latent_signal(selection_dict: dict[str, Any]) -> str:
    candidates = list(selection_dict.get("candidates", []) or [])
    selected_index = int(selection_dict.get("selected_index", 0))
    if 0 <= selected_index < len(candidates):
        selected = candidates[selected_index] or {}
        if isinstance(selected, dict):
            return str(selected.get("latent_signal", ""))
    return ""
