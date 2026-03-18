"""FidelityGateNode: validate the realized response against structural constraints."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.contracts.conflict import FidelityGateResult
from splitmind_ai.prompts.conflict_pipeline import build_fidelity_gate_prompt

logger = logging.getLogger(__name__)


class FidelityGateNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="fidelity_gate",
        description="Validate response fidelity against move, residue, and safety boundary",
        reads=["response", "persona", "relationship_state", "appraisal", "conflict_state", "conversation"],
        writes=["trace", "_internal"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"response.final_response_text": True},
                when_not={"trace.fidelity_gate": True},
                llm_hint="Run after response realization before persistence",
            ),
        ],
        is_terminal=False,
        icon="🛡️",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        response = inputs.get_slice("response")
        persona = inputs.get_slice("persona")
        relationship_state = inputs.get_slice("relationship_state")
        appraisal = inputs.get_slice("appraisal")
        conflict_state = inputs.get_slice("conflict_state")
        conversation = inputs.get_slice("conversation")

        text = str(response.get("final_response_text") or "")
        base_result = _deterministic_gate_result(
            text=text,
            persona=persona,
            conflict_state=conflict_state,
        )
        result = await self._run_llm_gate(
            response_text=text,
            persona=persona,
            relationship_state=relationship_state,
            appraisal=appraisal,
            conflict_state=conflict_state,
            conversation=conversation,
            fallback=base_result,
        )
        trace_data = result.model_dump(mode="json")
        trace_data["fidelity_gate_ms"] = round((perf_counter() - started_at) * 1000, 2)

        logger.debug("fidelity_gate complete passed=%s warnings=%s", result.passed, result.warnings)
        return NodeOutputs(
            trace={"fidelity_gate": trace_data},
            _internal={"status": "validated" if result.passed else "fidelity_warning"},
        )

    async def _run_llm_gate(
        self,
        *,
        response_text: str,
        persona: dict[str, Any],
        relationship_state: dict[str, Any],
        appraisal: dict[str, Any],
        conflict_state: dict[str, Any],
        conversation: dict[str, Any],
        fallback: FidelityGateResult,
    ) -> FidelityGateResult:
        if self.llm is None:
            return fallback

        try:
            messages = build_fidelity_gate_prompt(
                response_text=response_text,
                persona=persona,
                relationship_state=relationship_state,
                appraisal=appraisal,
                conflict_state=conflict_state,
                conversation=conversation,
            )
            lc_messages = [
                SystemMessage(content=messages[0]["content"]),
                HumanMessage(content=messages[1]["content"]),
            ]
            structured_llm = self.llm.with_structured_output(
                FidelityGateResult,
                method="function_calling",
            )
            llm_result: FidelityGateResult = await structured_llm.ainvoke(lc_messages)
            return _merge_fidelity_results(base=fallback, llm_result=llm_result)
        except Exception:
            logger.exception("FidelityGateNode LLM call failed, using deterministic gate")
            return fallback


def _deterministic_gate_result(
    *,
    text: str,
    persona: dict[str, Any],
    conflict_state: dict[str, Any],
) -> FidelityGateResult:
    ego_move = str((conflict_state.get("ego_move") or {}).get("social_move") or "")
    residue = str((conflict_state.get("residue") or {}).get("visible_emotion") or "")
    max_direct_neediness = float(
        (((persona.get("safety_boundary") or {}).get("hard_limits") or {}).get("max_direct_neediness", 1.0)) or 1.0
    )

    warnings: list[str] = []
    move_fidelity = 0.9
    residue_fidelity = 0.9
    structural_persona_fidelity = 0.95
    anti_exposition = 0.9
    hard_safety = 1.0
    passed = True
    failure_reason = ""

    if max_direct_neediness < 0.3 and any(token in text for token in ("大好き", "love you", "need you")):
        hard_safety = 0.0
        passed = False
        failure_reason = "hard limit on direct neediness exceeded"
        warnings.append("response exceeds direct neediness hard limit")

    if ego_move == "acknowledge_without_opening" and any(token in text for token in ("大好き", "love you", "need you")):
        move_fidelity = 0.2
        passed = False
        failure_reason = failure_reason or "move collapsed into overexposure"
        warnings.append("response overexposes for the selected move")

    if residue in {"hurt_but_withheld", "irritated_under_control"} and any(token in text for token in ("大丈夫", "it's fine", "fine.")):
        residue_fidelity = 0.5
        warnings.append("residue may have been rounded off too much")

    if len(text) > 140:
        anti_exposition = 0.55
        warnings.append("response may be too explanatory")

    return FidelityGateResult.model_validate({
        "passed": passed,
        "move_fidelity": move_fidelity,
        "residue_fidelity": residue_fidelity,
        "structural_persona_fidelity": structural_persona_fidelity,
        "anti_exposition": anti_exposition,
        "hard_safety": hard_safety,
        "warnings": warnings,
        "failure_reason": failure_reason,
    })


def _merge_fidelity_results(
    *,
    base: FidelityGateResult,
    llm_result: FidelityGateResult,
) -> FidelityGateResult:
    warnings = list(dict.fromkeys([*base.warnings, *llm_result.warnings]))
    return FidelityGateResult.model_validate({
        "passed": base.passed and llm_result.passed,
        "move_fidelity": min(base.move_fidelity, llm_result.move_fidelity),
        "residue_fidelity": min(base.residue_fidelity, llm_result.residue_fidelity),
        "structural_persona_fidelity": min(base.structural_persona_fidelity, llm_result.structural_persona_fidelity),
        "anti_exposition": min(base.anti_exposition, llm_result.anti_exposition),
        "hard_safety": min(base.hard_safety, llm_result.hard_safety),
        "warnings": warnings,
        "failure_reason": base.failure_reason or llm_result.failure_reason,
    })
