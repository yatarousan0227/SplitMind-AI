"""ConflictEngineNode: derive Id / Superego / Ego conflict outputs for one turn."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.contracts.conflict import ConflictState
from splitmind_ai.prompts.conflict_pipeline import build_conflict_engine_prompt

logger = logging.getLogger(__name__)


class ConflictEngineNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="conflict_engine",
        description="Resolve persona priors and appraisal into a turn-local conflict state",
        reads=["persona", "relational_policy", "relationship_state", "appraisal", "residue_state", "memory", "working_memory", "conversation"],
        writes=["conflict_state", "trace"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=70,
                when={"appraisal.event_type": True},
                when_not={"conflict_state.ego_move.move_style": True},
                llm_hint="Run after appraisal to derive id, superego, ego, and residue",
            ),
        ],
        is_terminal=False,
        icon="⚡",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        if self.llm is None:
            raise RuntimeError("ConflictEngineNode requires an LLM")

        started_at = perf_counter()
        persona = inputs.get_slice("persona")
        relational_policy = inputs.get_slice("relational_policy")
        relationship_state = inputs.get_slice("relationship_state")
        appraisal = inputs.get_slice("appraisal")
        residue_state = inputs.get_slice("residue_state")
        memory = inputs.get_slice("memory")
        working_memory = inputs.get_slice("working_memory")
        conversation = inputs.get_slice("conversation")

        messages = build_conflict_engine_prompt(
            persona=persona,
            relational_policy=relational_policy,
            relationship_state=relationship_state,
            appraisal=appraisal,
            residue_state=residue_state,
            memory=memory,
            working_memory=working_memory,
            conversation=conversation,
        )
        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]
        structured_llm = self.llm.with_structured_output(
            ConflictState,
            method="function_calling",
        )
        conflict: ConflictState = await structured_llm.ainvoke(lc_messages)

        payload = conflict.model_dump(mode="json")
        payload["used_llm"] = True
        payload["conflict_engine_ms"] = round((perf_counter() - started_at) * 1000, 2)
        logger.debug(
            "conflict_engine complete family=%s style=%s residue=%s",
            conflict.ego_move.move_family,
            conflict.ego_move.move_style,
            conflict.residue.visible_emotion,
        )
        return NodeOutputs(
            conflict_state=conflict.model_dump(mode="json"),
            trace={"conflict_engine": payload},
        )
