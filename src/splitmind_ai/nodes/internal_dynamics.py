"""InternalDynamicsNode: Call 1 — produce Id/Ego/Superego/Defense analysis.

Reads: request, conversation, persona, relationship, mood, memory, _internal.session
Writes: dynamics, trace.internal_dynamics, _internal.event_flags
Trigger: request.user_message exists
"""

from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.app.logging_utils import preview_text
from splitmind_ai.contracts.dynamics import InternalDynamicsBundle
from splitmind_ai.prompts.internal_dynamics import build_internal_dynamics_prompt

logger = logging.getLogger(__name__)


class InternalDynamicsNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="internal_dynamics",
        description="Generate Id/Ego/Superego/Defense structured reasoning (Call 1)",
        reads=[
            "request",
            "conversation",
            "persona",
            "relationship",
            "mood",
            "memory",
            "_internal",
        ],
        writes=["dynamics", "trace", "_internal"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=80,
                when={"request.user_message": True},
                when_not={"dynamics.id_output": True},
                llm_hint="Run when a user message is present for internal reasoning",
            ),
        ],
        is_terminal=False,
        icon="🧠",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        request = inputs.get_slice("request")
        conversation = inputs.get_slice("conversation")
        persona = inputs.get_slice("persona")
        relationship = inputs.get_slice("relationship")
        mood = inputs.get_slice("mood")
        memory = inputs.get_slice("memory")

        user_message = request.get("user_message", "")
        recent = conversation.get("recent_messages", [])
        logger.debug(
            "internal_dynamics start session_id=%s recent_count=%s message=%s",
            inputs.get_slice("_internal").get("session", {}).get("session_id"),
            len(recent),
            preview_text(user_message),
        )

        messages = build_internal_dynamics_prompt(
            user_message=user_message,
            conversation_context=recent,
            persona=persona,
            relationship=relationship,
            mood=mood,
            memory=memory,
        )

        # Call LLM with structured output
        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]

        if self.llm is None:
            logger.warning("InternalDynamicsNode LLM unavailable, using fallback")
            result = _fallback_dynamics()
        else:
            try:
                structured_llm = self.llm.with_structured_output(
                    InternalDynamicsBundle,
                    method="function_calling",
                )
                result: InternalDynamicsBundle = await structured_llm.ainvoke(lc_messages)
            except Exception:
                logger.exception("InternalDynamicsNode LLM call failed, using fallback")
                result = _fallback_dynamics()

        dynamics_dict = result.model_dump()
        active_flags = [k for k, v in dynamics_dict.get("event_flags", {}).items() if v]
        logger.debug(
            "internal_dynamics complete dominant_desire=%s pressure=%.2f active_flags=%s",
            dynamics_dict["dominant_desire"],
            dynamics_dict["id_output"]["affective_pressure_score"],
            active_flags,
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)

        return NodeOutputs(
            dynamics={
                "id_output": dynamics_dict["id_output"],
                "ego_output": dynamics_dict["ego_output"],
                "superego_output": dynamics_dict["superego_output"],
                "defense_output": dynamics_dict["defense_output"],
                "drive_axes": dynamics_dict["id_output"]["drive_axes"],
                "target_lock": dynamics_dict["id_output"]["target_lock"],
                "suppression_risk": dynamics_dict["id_output"]["suppression_risk"],
                "dominant_desire": dynamics_dict["dominant_desire"],
                "affective_pressure": dynamics_dict["id_output"]["affective_pressure_score"],
            },
            trace={"internal_dynamics": {**dynamics_dict, "internal_dynamics_ms": elapsed_ms}},
            _internal={"event_flags": dynamics_dict.get("event_flags", {})},
        )


def _fallback_dynamics() -> InternalDynamicsBundle:
    """Return a safe fallback when the LLM call fails."""
    return InternalDynamicsBundle.model_validate({
        "id_output": {
            "raw_desire_candidates": [
                {
                    "desire_type": "neutral_engagement",
                    "intensity": 0.3,
                    "target": "conversation",
                    "direction": "approach",
                    "rationale": "Fallback: maintain basic engagement",
                }
            ],
            "drive_axes": [
                {
                    "name": "curiosity_approach",
                    "value": 0.3,
                    "target": "conversation",
                    "urgency": 0.2,
                    "frustration": 0.0,
                    "satiation": 0.0,
                    "carryover": 0.1,
                    "suppression_load": 0.1,
                }
            ],
            "affective_pressure_score": 0.2,
            "approach_avoidance_balance": 0.6,
            "target_lock": 0.2,
            "suppression_risk": 0.15,
            "impulse_summary": "Low-pressure fallback engagement",
        },
        "ego_output": {
            "response_strategy": "neutral_acknowledgment",
            "risk_assessment": "low",
            "concealment_or_reveal_plan": "Minimal reveal",
            "softening_note": None,
        },
        "superego_output": {
            "role_alignment_score": 0.8,
            "ideal_self_gap": 0.1,
            "shame_or_guilt_pressure": 0.0,
            "violation_flags": [],
            "norm_note": "Fallback safe mode",
        },
        "defense_output": {
            "selected_mechanism": "suppression",
            "transformation_note": "Suppress internal state during fallback",
            "leakage_recommendation": 0.1,
        },
        "dominant_desire": "neutral_engagement",
        "event_flags": {},
    })
