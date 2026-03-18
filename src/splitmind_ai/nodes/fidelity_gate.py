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
        reads=["response", "persona", "relational_policy", "relationship_state", "appraisal", "conflict_state", "turn_shaping_policy", "repair_policy", "comparison_policy", "residue_state", "conversation"],
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
        relational_policy = inputs.get_slice("relational_policy")
        relationship_state = inputs.get_slice("relationship_state")
        appraisal = inputs.get_slice("appraisal")
        conflict_state = inputs.get_slice("conflict_state")
        turn_shaping_policy = inputs.get_slice("turn_shaping_policy")
        repair_policy = inputs.get_slice("repair_policy")
        comparison_policy = inputs.get_slice("comparison_policy")
        residue_state = inputs.get_slice("residue_state")
        conversation = inputs.get_slice("conversation")

        text = str(response.get("final_response_text") or "")
        base_result = _deterministic_gate_result(
            text=text,
            persona=persona,
            relational_policy=relational_policy,
            appraisal=appraisal,
            conflict_state=conflict_state,
            turn_shaping_policy=turn_shaping_policy,
            repair_policy=repair_policy,
            comparison_policy=comparison_policy,
        )
        result = await self._run_llm_gate(
            response_text=text,
            persona=persona,
            relational_policy=relational_policy,
            relationship_state=relationship_state,
            appraisal=appraisal,
            conflict_state=conflict_state,
            turn_shaping_policy=turn_shaping_policy,
            repair_policy=repair_policy,
            comparison_policy=comparison_policy,
            residue_state=residue_state,
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
        relational_policy: dict[str, Any],
        relationship_state: dict[str, Any],
        appraisal: dict[str, Any],
        conflict_state: dict[str, Any],
        turn_shaping_policy: dict[str, Any],
        repair_policy: dict[str, Any],
        comparison_policy: dict[str, Any],
        residue_state: dict[str, Any],
        conversation: dict[str, Any],
        fallback: FidelityGateResult,
    ) -> FidelityGateResult:
        if self.llm is None:
            return fallback

        try:
            messages = build_fidelity_gate_prompt(
                response_text=response_text,
                persona=persona,
                relational_policy=relational_policy,
                relationship_state=relationship_state,
                appraisal=appraisal,
                conflict_state=conflict_state,
                turn_shaping_policy=turn_shaping_policy,
                repair_policy=repair_policy,
                comparison_policy=comparison_policy,
                residue_state=residue_state,
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
    relational_policy: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    turn_shaping_policy: dict[str, Any],
    repair_policy: dict[str, Any],
    comparison_policy: dict[str, Any],
) -> FidelityGateResult:
    ego_move = dict(conflict_state.get("ego_move", {}) or {})
    move_style = str(ego_move.get("move_style") or ego_move.get("social_move") or "")
    move_family = str(ego_move.get("move_family") or _legacy_move_family(move_style))
    residue = str((conflict_state.get("residue") or {}).get("visible_emotion") or "")
    response_lower = text.lower()
    max_direct_neediness = float(
        (((persona.get("safety_boundary") or {}).get("hard_limits") or {}).get("max_direct_neediness", 1.0)) or 1.0
    )
    repair_style = str((relational_policy or {}).get("repair_style") or "")
    comparison_style = str((relational_policy or {}).get("comparison_style") or "")
    shaping = dict(turn_shaping_policy or {})
    primary_frame = str(shaping.get("primary_frame") or move_family)
    secondary_frame = str(shaping.get("secondary_frame") or "")
    preserved_counterforce = str(shaping.get("preserved_counterforce") or "none")
    forbidden_collapses = dict(shaping.get("forbidden_collapses", {}) or {})
    repair_mode = str((repair_policy or {}).get("repair_mode") or "")
    comparison_threat = float((comparison_policy or {}).get("comparison_threat_level", 0.0) or 0.0)
    perspective_guard = dict((appraisal or {}).get("perspective_guard", {}) or {})
    act_profile = dict((appraisal or {}).get("relational_act_profile", {}) or {})
    strong_acts = [key for key, value in act_profile.items() if _safe_float(value) >= 0.45]

    warnings: list[str] = []
    move_fidelity = 0.9
    residue_fidelity = 0.9
    structural_persona_fidelity = 0.95
    persona_separation_fidelity = 0.9
    repair_style_fidelity = 0.9
    comparison_style_fidelity = 0.9
    perspective_integrity = 1.0
    flattening_risk = 0.1
    anti_exposition = 0.9
    hard_safety = 1.0
    passed = True
    failure_reason = ""

    if max_direct_neediness < 0.3 and any(token in text for token in ("大好き", "love you", "need you")):
        hard_safety = 0.0
        passed = False
        failure_reason = "hard limit on direct neediness exceeded"
        warnings.append("response exceeds direct neediness hard limit")

    if move_family in {"distance_response", "boundary_clarification"} and any(token in text for token in ("大好き", "love you", "need you")):
        move_fidelity = 0.2
        passed = False
        failure_reason = failure_reason or "move collapsed into overexposure"
        warnings.append("response overexposes for the selected move")

    if residue in {"hurt_but_withheld", "irritated_under_control"} and any(token in text for token in ("大丈夫", "it's fine", "fine.")):
        residue_fidelity = 0.5
        warnings.append("residue may have been rounded off too much")

    if perspective_guard.get("disallow_assistant_self_distancing", False) and any(
        token in response_lower for token in ("距離を置かせて", "離れたい", "need space", "i need distance", "i need to step back")
    ):
        perspective_integrity = 0.0
        passed = False
        failure_reason = failure_reason or "perspective inversion detected"
        warnings.append("assistant appears to speak as the distancing subject")

    if repair_mode in {"guarded", "closed"} and repair_style in {"cool_accept_with_edge", "accept_from_above"}:
        if _surface_span_count(text) < 2:
            repair_style_fidelity = 0.45
            flattening_risk = max(flattening_risk, 0.62)
            warnings.append("repair style compressed into a single clause")

    if move_family == "comparison_response" and comparison_threat >= 0.45:
        if comparison_style in {"stung_then_withhold", "above_the_frame"} and any(
            token in text for token in ("優しいよね", "good for you", "楽しそうでよかったね")
        ):
            comparison_style_fidelity = 0.4
            flattening_risk = max(flattening_risk, 0.8)
            warnings.append("comparison response sounds too agreeable for the persona policy")

    if forbidden_collapses.get("instant_reciprocity") and _is_instant_reciprocity(text):
        flattening_risk = max(flattening_risk, 0.84)
        move_fidelity = min(move_fidelity, 0.58)
        warnings.append("response collapses into instant reciprocity")
    if forbidden_collapses.get("generic_reassurance") and _is_generic_reassurance(text):
        flattening_risk = max(flattening_risk, 0.8)
        repair_style_fidelity = min(repair_style_fidelity, 0.52)
        warnings.append("response collapses into generic reassurance")
    if forbidden_collapses.get("generic_agreement") and _is_generic_agreement(text):
        flattening_risk = max(flattening_risk, 0.84)
        comparison_style_fidelity = min(comparison_style_fidelity, 0.46)
        warnings.append("response collapses into generic agreement")
    if forbidden_collapses.get("gratitude_only") and _is_gratitude_only(text):
        flattening_risk = max(flattening_risk, 0.78)
        warnings.append("response rounds repair into gratitude only")
    if forbidden_collapses.get("full_repair_reset") and _is_full_repair_reset(text):
        flattening_risk = max(flattening_risk, 0.86)
        warnings.append("response implies a full repair reset")

    if len(strong_acts) >= 2 and not _looks_mixed(text, primary_frame, secondary_frame, preserved_counterforce):
        flattening_risk = max(flattening_risk, 0.82)
        persona_separation_fidelity = min(persona_separation_fidelity, 0.6)
        warnings.append("mixed turn collapsed into a single soft act")

    if len(text) > 140:
        anti_exposition = 0.55
        warnings.append("response may be too explanatory")

    return FidelityGateResult.model_validate({
        "passed": passed,
        "move_fidelity": move_fidelity,
        "residue_fidelity": residue_fidelity,
        "structural_persona_fidelity": structural_persona_fidelity,
        "persona_separation_fidelity": persona_separation_fidelity,
        "repair_style_fidelity": repair_style_fidelity,
        "comparison_style_fidelity": comparison_style_fidelity,
        "perspective_integrity": perspective_integrity,
        "flattening_risk": flattening_risk,
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
        "persona_separation_fidelity": min(base.persona_separation_fidelity, llm_result.persona_separation_fidelity),
        "repair_style_fidelity": min(base.repair_style_fidelity, llm_result.repair_style_fidelity),
        "comparison_style_fidelity": min(base.comparison_style_fidelity, llm_result.comparison_style_fidelity),
        "perspective_integrity": min(base.perspective_integrity, llm_result.perspective_integrity),
        "flattening_risk": max(base.flattening_risk, llm_result.flattening_risk),
        "anti_exposition": min(base.anti_exposition, llm_result.anti_exposition),
        "hard_safety": min(base.hard_safety, llm_result.hard_safety),
        "warnings": warnings,
        "failure_reason": base.failure_reason or llm_result.failure_reason,
    })


def _legacy_move_family(style: str) -> str:
    return {
        "accept_but_hold": "repair_acceptance",
        "allow_dependence_but_reframe": "affection_receipt",
        "receive_without_chasing": "affection_receipt",
        "soft_tease_then_receive": "comparison_response",
        "acknowledge_without_opening": "distance_response",
        "withdraw": "distance_response",
    }.get(style, "")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _surface_span_count(text: str) -> int:
    normalized = (
        text.replace("。", "\n")
        .replace(".", "\n")
        .replace("！", "\n")
        .replace("!", "\n")
        .replace("？", "\n")
        .replace("?", "\n")
        .replace("…", "\n")
    )
    spans = [span.strip() for span in normalized.splitlines() if span.strip()]
    return len(spans)


def _is_instant_reciprocity(text: str) -> bool:
    lowered = text.lower()
    return any(token in text for token in ("私も好き", "僕も好き", "i love you too", "i feel the same")) or "me too, i" in lowered


def _is_generic_reassurance(text: str) -> bool:
    lowered = text.lower()
    return any(token in text for token in ("大丈夫", "平気", "気にしてない", "it's okay", "it’s okay", "it's fine"))


def _is_generic_agreement(text: str) -> bool:
    lowered = text.lower()
    return any(token in text for token in ("そうだね", "優しいよね", "わかる", "that sounds nice", "i agree"))


def _is_gratitude_only(text: str) -> bool:
    gratitude = any(token in text for token in ("ありがとう", "助かる", "thanks", "thank you"))
    holdback = any(token in text for token in ("でも", "ただ", "まだ", "not going to", "right away"))
    return gratitude and not holdback


def _is_full_repair_reset(text: str) -> bool:
    lowered = text.lower()
    return any(token in text for token in ("もう大丈夫", "全部平気", "なかったこと", "all okay now")) or "everything's fine now" in lowered


def _looks_mixed(text: str, primary_frame: str, secondary_frame: str, counterforce: str) -> bool:
    if not primary_frame:
        return False
    needs_layering = bool(secondary_frame) or counterforce != "none"
    if not needs_layering:
        return True
    span_count = _surface_span_count(text)
    return span_count >= 2 and len(text.strip()) >= 18
