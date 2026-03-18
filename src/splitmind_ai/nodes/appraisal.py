"""AppraisalNode: convert the latest user turn into a relational event appraisal."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.app.relational_cues import merge_appraisal_with_cue_parse
from splitmind_ai.contracts.appraisal import RelationalCueParse, StimulusAppraisal
from splitmind_ai.prompts.conflict_pipeline import build_appraisal_prompt, build_relational_cue_prompt

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
        cue_messages = build_relational_cue_prompt(
            user_message=str(request.get("user_message", "")),
            relationship_state=relationship_state,
            working_memory=working_memory,
            conversation=conversation,
        )
        cue_lc_messages = [
            SystemMessage(content=cue_messages[0]["content"]),
            HumanMessage(content=cue_messages[1]["content"]),
        ]
        cue_llm = self.llm.with_structured_output(
            RelationalCueParse,
            method="function_calling",
        )
        cue_parse: RelationalCueParse = await cue_llm.ainvoke(cue_lc_messages)

        messages = build_appraisal_prompt(
            user_message=str(request.get("user_message", "")),
            persona=persona,
            relationship_state=relationship_state,
            relational_cue_parse=cue_parse.model_dump(mode="json"),
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
        merged_payload = merge_appraisal_with_cue_parse(
            llm_appraisal=appraisal.model_dump(mode="json"),
            cue_parse=cue_parse.model_dump(mode="json"),
        )
        appraisal = StimulusAppraisal.model_validate(merged_payload)

        payload = appraisal.model_dump(mode="json")
        payload["relational_cue_parse"] = cue_parse.model_dump(mode="json")
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
