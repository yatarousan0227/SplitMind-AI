"""AppraisalNode: convert the latest user turn into a relational event appraisal."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.contracts.appraisal import StimulusAppraisal
from splitmind_ai.prompts.conflict_pipeline import build_appraisal_prompt

logger = logging.getLogger(__name__)


class AppraisalNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="appraisal",
        description="Interpret the user turn as a relational event",
        reads=["request", "persona", "relationship_state", "working_memory", "conversation"],
        writes=["appraisal", "trace"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=80,
                when={"request.user_message": True},
                when_not={"appraisal.event_type": True},
                llm_hint="Run after bootstrap to classify the current relational event",
            ),
        ],
        is_terminal=False,
        icon="🧭",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        if self.llm is None:
            raise RuntimeError("AppraisalNode requires an LLM")

        started_at = perf_counter()
        request = inputs.get_slice("request")
        persona = inputs.get_slice("persona")
        relationship_state = inputs.get_slice("relationship_state")
        working_memory = inputs.get_slice("working_memory")
        conversation = inputs.get_slice("conversation")

        messages = build_appraisal_prompt(
            user_message=str(request.get("user_message", "")),
            persona=persona,
            relationship_state=relationship_state,
            working_memory=working_memory,
            conversation=conversation,
        )
        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]
        structured_llm = self.llm.with_structured_output(
            StimulusAppraisal,
            method="function_calling",
        )
        appraisal: StimulusAppraisal = await structured_llm.ainvoke(lc_messages)

        payload = appraisal.model_dump(mode="json")
        payload["used_llm"] = True
        payload["appraisal_ms"] = round((perf_counter() - started_at) * 1000, 2)
        logger.debug(
            "appraisal complete event_type=%s target=%s stakes=%s",
            appraisal.event_type.value,
            appraisal.target_of_tension.value,
            appraisal.stakes.value,
        )
        return NodeOutputs(
            appraisal=appraisal.model_dump(mode="json"),
            trace={"appraisal": payload},
        )
