"""MemoryInterpreterNode: interpret turn-end persistence artifacts with an LLM."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.contracts.memory import MemoryInterpretation
from splitmind_ai.prompts.conflict_pipeline import build_memory_interpreter_prompt

logger = logging.getLogger(__name__)


class MemoryInterpreterNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="memory_interpreter",
        description="Interpret the completed turn into persistence artifacts",
        reads=[
            "request",
            "response",
            "conversation",
            "persona",
            "relationship_state",
            "mood",
            "memory",
            "working_memory",
            "appraisal",
            "conflict_state",
            "drive_state",
            "_internal",
        ],
        writes=["memory_interpretation", "trace", "_internal"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=45,
                when={"trace.fidelity_gate": True},
                when_not={"trace.memory_interpreter": True},
                llm_hint="Run after fidelity validation to interpret persistence artifacts",
            ),
        ],
        is_terminal=False,
        icon="🧠",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        if self.llm is None:
            raise RuntimeError("MemoryInterpreterNode requires an LLM")

        started_at = perf_counter()
        request = inputs.get_slice("request")
        response = inputs.get_slice("response")
        conversation = inputs.get_slice("conversation")
        persona = inputs.get_slice("persona")
        relationship_state = inputs.get_slice("relationship_state")
        mood = inputs.get_slice("mood")
        memory = inputs.get_slice("memory")
        working_memory = inputs.get_slice("working_memory")
        appraisal = inputs.get_slice("appraisal")
        conflict_state = inputs.get_slice("conflict_state")
        drive_state = inputs.get_slice("drive_state")

        messages = build_memory_interpreter_prompt(
            request=request,
            response=response,
            persona=persona,
            relationship_state=relationship_state,
            mood=mood,
            memory=memory,
            working_memory=working_memory,
            appraisal=appraisal,
            conflict_state=conflict_state,
            drive_state=drive_state,
            conversation=conversation,
        )
        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]
        structured_llm = self.llm.with_structured_output(
            MemoryInterpretation,
            method="function_calling",
        )
        interpretation: MemoryInterpretation = await structured_llm.ainvoke(lc_messages)

        payload = interpretation.model_dump(mode="json")
        payload["used_llm"] = True
        payload["memory_interpreter_ms"] = round((perf_counter() - started_at) * 1000, 2)
        logger.debug(
            "memory_interpreter complete event_flags=%s emotional_memories=%s semantic_preferences=%s",
            sorted(k for k, v in interpretation.event_flags.items() if v),
            len(interpretation.emotional_memories),
            len(interpretation.semantic_preferences),
        )
        return NodeOutputs(
            memory_interpretation=interpretation.model_dump(mode="json"),
            trace={"memory_interpreter": payload},
            _internal={"event_flags": interpretation.event_flags},
        )
