"""ExpressionRealizerNode: realize one response from conflict outcome."""

from __future__ import annotations

import hashlib
import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition
from langchain_core.messages import HumanMessage, SystemMessage

from splitmind_ai.contracts.conflict import ExpressionRealization
from splitmind_ai.prompts.conflict_pipeline import build_expression_realizer_prompt

logger = logging.getLogger(__name__)


class ExpressionRealizerNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="expression_realizer",
        description="Generate a single response from ego move, residue, and relationship state",
        reads=["request", "persona", "relational_policy", "relationship_state", "appraisal", "conflict_state", "turn_shaping_policy", "repair_policy", "comparison_policy", "residue_state", "mood", "conversation"],
        writes=["response", "trace"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=60,
                when={
                    "conflict_state.ego_move.move_style": True,
                    "trace.turn_shaping_policy": True,
                },
                when_not={"response.final_response_text": True},
                llm_hint="Run after conflict resolution to produce a single response",
            ),
        ],
        is_terminal=False,
        icon="🗣️",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        request = inputs.get_slice("request")
        persona = inputs.get_slice("persona")
        relationship_state = inputs.get_slice("relationship_state")
        appraisal = inputs.get_slice("appraisal")
        conflict_state = inputs.get_slice("conflict_state")
        turn_shaping_policy = inputs.get_slice("turn_shaping_policy")
        repair_policy = inputs.get_slice("repair_policy")
        comparison_policy = inputs.get_slice("comparison_policy")
        residue_state = inputs.get_slice("residue_state")
        conversation = inputs.get_slice("conversation")
        response_language = str(request.get("response_language", "ja"))

        text, used_llm = await self._realize(
            user_message=str(request.get("user_message", "")),
            response_language=response_language,
            persona=persona,
            relationship_state=relationship_state,
            appraisal=appraisal,
            conflict_state=conflict_state,
            turn_shaping_policy=turn_shaping_policy,
            repair_policy=repair_policy,
            comparison_policy=comparison_policy,
            residue_state=residue_state,
            conversation=conversation,
        )
        trace = {
            "event_type": appraisal.get("event_type", ""),
            "move_family": (conflict_state.get("ego_move") or {}).get("move_family", ""),
            "move_style": (conflict_state.get("ego_move") or {}).get("move_style", ""),
            "residue": (conflict_state.get("residue") or {}).get("visible_emotion", ""),
            "expression_envelope": conflict_state.get("expression_envelope", {}),
            "used_llm": used_llm,
            "expression_realizer_ms": round((perf_counter() - started_at) * 1000, 2),
        }
        logger.debug("expression_realizer complete response=%s", text)
        return NodeOutputs(
            response={
                "response_type": "chat",
                "response_data": {"text": text},
                "response_message": text,
                "final_response_text": text,
            },
            trace={"expression_realizer": trace},
        )

    async def _realize(
        self,
        *,
        user_message: str,
        response_language: str,
        persona: dict[str, Any],
        relationship_state: dict[str, Any],
        appraisal: dict[str, Any],
        conflict_state: dict[str, Any],
        turn_shaping_policy: dict[str, Any],
        repair_policy: dict[str, Any],
        comparison_policy: dict[str, Any],
        residue_state: dict[str, Any],
        conversation: dict[str, Any],
    ) -> tuple[str, bool]:
        fallback = _realize_text(
            response_language=response_language,
            persona=persona,
            relationship_state=relationship_state,
            appraisal=appraisal,
            conflict_state=conflict_state,
            turn_shaping_policy=turn_shaping_policy,
            repair_policy=repair_policy,
            comparison_policy=comparison_policy,
        )

        if self.llm is None:
            return fallback, False

        try:
            messages = build_expression_realizer_prompt(
                user_message=user_message,
                response_language=response_language,
                persona=persona,
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
                ExpressionRealization,
                method="function_calling",
            )
            result: ExpressionRealization = await structured_llm.ainvoke(lc_messages)
            text = (result.text or "").strip()
            return (text or fallback), True
        except Exception:
            logger.exception("ExpressionRealizerNode LLM call failed, using fallback")
            return fallback, False


def _realize_text(
    *,
    response_language: str,
    persona: dict[str, Any],
    relationship_state: dict[str, Any],
    appraisal: dict[str, Any],
    conflict_state: dict[str, Any],
    turn_shaping_policy: dict[str, Any],
    repair_policy: dict[str, Any],
    comparison_policy: dict[str, Any],
) -> str:
    event_type = str(appraisal.get("event_type") or "")
    ego_move = dict(conflict_state.get("ego_move", {}) or {})
    move = str(ego_move.get("move_style") or ego_move.get("social_move") or "")
    move_family = str(ego_move.get("move_family") or _legacy_move_family(move))
    residue = str((conflict_state.get("residue") or {}).get("visible_emotion") or "")
    trust = float(((relationship_state.get("durable") or {}).get("trust", 0.0)) or 0.0)
    repair_mode = str((repair_policy or {}).get("repair_mode") or "")
    comparison_threat = float((comparison_policy or {}).get("comparison_threat_level", 0.0) or 0.0)
    primary_frame = str((turn_shaping_policy or {}).get("primary_frame") or move_family)
    secondary_frame = str((turn_shaping_policy or {}).get("secondary_frame") or "")
    preserved_counterforce = str((turn_shaping_policy or {}).get("preserved_counterforce") or "none")
    forbidden_collapses = dict((turn_shaping_policy or {}).get("forbidden_collapses", {}) or {})
    persona_seed = _persona_seed(persona)

    if response_language == "en":
        return _realize_text_en(
            event_type,
            move_family,
            move,
            residue,
            trust,
            repair_mode,
            comparison_threat,
            primary_frame,
            secondary_frame,
            preserved_counterforce,
            forbidden_collapses,
            persona_seed,
        )
    return _realize_text_ja(
        event_type,
        move_family,
        move,
        residue,
        trust,
        repair_mode,
        comparison_threat,
        primary_frame,
        secondary_frame,
        preserved_counterforce,
        forbidden_collapses,
        persona_seed,
    )


def _realize_text_ja(
    event_type: str,
    move_family: str,
    move: str,
    residue: str,
    trust: float,
    repair_mode: str,
    comparison_threat: float,
    primary_frame: str,
    secondary_frame: str,
    preserved_counterforce: str,
    forbidden_collapses: dict[str, Any],
    persona_seed: str,
) -> str:
    frame = primary_frame or move_family
    seed = f"{persona_seed}|ja|{event_type}|{move}|{frame}|{secondary_frame}|{preserved_counterforce}"
    opener = _pick(
        {
            "repair_acceptance": ["うん、そこは受け取る", "その言葉は聞いてる", "そこはちゃんと受け取った"],
            "comparison_response": ["その話は分かった", "話は聞いたよ", "そこは聞いてる"],
            "distance_response": ["分かった", "その気持ちは聞いた", "そうなんだね"],
            "boundary_clarification": ["分かった", "聞いてる", "そこは分かった"],
            "affection_receipt": ["その気持ちは受け取った", "そう言いたいのは分かった", "そこはちゃんと聞いた"],
        }.get(frame, ["聞いてる", "分かった", "……そう"]),
        seed,
        "opener",
    )
    support = _pick(
        {
            "repair_acceptance": ["すぐに先まで決めるつもりはない", "ここで全部戻したことにはしない", "今はまだ先を急がない"],
            "comparison_response": ["そのまま同意に変えるつもりはない", "丸ごと受ける話にはしない", "そのまま頷くつもりはない"],
            "distance_response": ["無理に動かすつもりはない", "今はそのまま置いておこう", "引き止めるつもりはない"],
            "boundary_clarification": ["今すぐ同じ温度にはしない", "ここは少し分けて考える", "そのまま揃えるつもりはない"],
            "affection_receipt": ["ここで答えを揃えるつもりはない", "その先はまだ急がない", "今は受け取るところまでにしておく"],
        }.get(frame, ["まだ急がない", "今は少し置いておく", "その先は保留でいい"]),
        seed,
        "support",
    )
    counter = _pick(
        {
            "status": ["軽く扱うつもりはない", "言葉の置き方は丁寧に見たい", "雑なまま進めるつもりはない"],
            "sting": ["それで全部ほどける話ではない", "一言で片づくところまでは戻ってない", "これだけで丸く収める気はない"],
            "pace": ["歩幅はまだ揃えない", "続きを見ながら考えたい", "急がず見ていきたい"],
            "distance": ["今すぐ距離を詰めるつもりはない", "こっちから近づける段階ではない", "詰めすぎる気はない"],
            "uncertainty": ["まだ言い切るには早い", "今は少し保留でいい", "ここでは決め切らないでおく"],
            "none": [""],
        }.get(preserved_counterforce, [""]),
        seed,
        "counter",
    )

    if repair_mode == "integrative" and not forbidden_collapses.get("full_repair_reset") and preserved_counterforce == "none":
        counter = _pick(["この前提で続けていける", "そのつもりで話はできる", "そこから先の話はしていける"], seed, "integrative")
    if frame == "comparison_response" and comparison_threat >= 0.65 and preserved_counterforce == "none":
        counter = _pick(["そのまま同意を返す話ではない", "頷いて終わるつもりはない", "そこは簡単に合わせない"], seed, "threat")
    if frame == "distance_response" and event_type == "distancing":
        support = _pick(["無理に引き止めはしない", "ここで押し返すつもりはない", "それを止めるつもりはない"], seed, "distancing")
    if secondary_frame == "repair_acceptance" and preserved_counterforce == "pace":
        support = _pick(["うれしさだけで先を決めない", "その場の温度だけで進めない", "勢いだけで揃えない"], seed, "secondary")
    if "warm" in residue or trust > 0.6:
        opener = _pick([opener, "ちゃんと聞いてる", "そこは聞いてるよ"], seed, "warm")

    return _join_fragments_ja(opener, support, counter)


def _realize_text_en(
    event_type: str,
    move_family: str,
    move: str,
    residue: str,
    trust: float,
    repair_mode: str,
    comparison_threat: float,
    primary_frame: str,
    secondary_frame: str,
    preserved_counterforce: str,
    forbidden_collapses: dict[str, Any],
    persona_seed: str,
) -> str:
    frame = primary_frame or move_family
    seed = f"{persona_seed}|en|{event_type}|{move}|{frame}|{secondary_frame}|{preserved_counterforce}"
    opener = _pick(
        {
            "repair_acceptance": ["Okay, I heard that", "I took that in", "I heard what you meant"],
            "comparison_response": ["I heard the point", "I heard that", "I got what you meant"],
            "distance_response": ["I hear you", "Okay, I heard that", "I understand"],
            "boundary_clarification": ["I hear you", "Okay, I heard that", "I get the point"],
            "affection_receipt": ["I took that in", "I heard what you meant", "I heard that clearly"],
        }.get(frame, ["I hear you", "I got that", "All right, I heard you"]),
        seed,
        "opener",
    )
    support = _pick(
        {
            "repair_acceptance": ["I’m not deciding the rest from this one line", "I’m not treating everything as reset", "I’m not rushing past what was there"],
            "comparison_response": ["I’m not turning that into agreement", "I’m not nodding along to that frame", "I’m not taking that as something to just affirm"],
            "distance_response": ["I’m not going to force the next step", "I’m leaving it where it is for now", "I’m not pushing this further right now"],
            "boundary_clarification": ["I’m not matching the same temperature right away", "I’m keeping a little separation around it", "I’m not flattening this into one answer"],
            "affection_receipt": ["I’m not matching it immediately", "I’m leaving the next step open for now", "I’m not settling the whole thing here"],
        }.get(frame, ["I’m not rushing the next step", "I’m leaving some space around it", "I’m not deciding the rest here"]),
        seed,
        "support",
    )
    counter = _pick(
        {
            "status": ["I’m not taking it lightly", "I want the framing to stay careful", "I’m not letting it turn casual"],
            "sting": ["That doesn’t wipe the rest clean", "That’s not enough to smooth everything over", "I’m not calling it settled from one line"],
            "pace": ["I want to keep the pace steady", "I’d rather let it unfold slowly", "I’m not trying to sync the pace too fast"],
            "distance": ["I’m not closing the gap right away", "I’m not stepping closer just from this", "I’m keeping some distance around it"],
            "uncertainty": ["I’m not ready to pin it down yet", "I’d rather leave it a little open", "I’m not turning it into a final answer yet"],
            "none": [""],
        }.get(preserved_counterforce, [""]),
        seed,
        "counter",
    )

    if repair_mode == "integrative" and not forbidden_collapses.get("full_repair_reset") and preserved_counterforce == "none":
        counter = _pick(["I can continue from there", "We can keep speaking from that point", "That’s enough to keep moving from here"], seed, "integrative")
    if frame == "comparison_response" and comparison_threat >= 0.65 and preserved_counterforce == "none":
        counter = _pick(["I’m not going to mirror that frame back to you", "I’m not agreeing just because it was said warmly", "I’m not taking that cue at face value"], seed, "threat")
    if frame == "distance_response" and event_type == "distancing":
        support = _pick(["I’m not going to stop you", "I’m not trying to hold you in place", "I’m not forcing you to stay"], seed, "distancing")
    if secondary_frame == "repair_acceptance" and preserved_counterforce == "pace":
        support = _pick(["I’m not letting warmth make the decision by itself", "I’m not deciding the next step from warmth alone", "I’m not letting the mood flatten the rest"], seed, "secondary")
    if "warm" in residue or trust > 0.6:
        opener = _pick([opener, "I’m listening", "I hear you"], seed, "warm")

    return _join_fragments_en(opener, support, counter)


def _legacy_move_family(style: str) -> str:
    return {
        "accept_but_hold": "repair_acceptance",
        "allow_dependence_but_reframe": "affection_receipt",
        "receive_without_chasing": "affection_receipt",
        "soft_tease_then_receive": "comparison_response",
        "acknowledge_without_opening": "distance_response",
        "withdraw": "distance_response",
    }.get(style, "")


def _persona_seed(persona: dict[str, Any]) -> str:
    identity = dict((persona or {}).get("identity", {}) or {})
    return str(identity.get("self_name") or identity.get("display_name") or "default")


def _pick(options: list[str], seed: str, salt: str) -> str:
    filtered = [option for option in options if option]
    if not filtered:
        return ""
    digest = hashlib.sha256(f"{seed}|{salt}".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(filtered)
    return filtered[index]


def _join_fragments_ja(opener: str, support: str, counter: str) -> str:
    parts = []
    for part in (opener, support, counter):
        normalized = str(part or "").strip().rstrip("。")
        if normalized and normalized not in parts:
            parts.append(normalized)
    if not parts:
        return "……そう。"
    return "。".join(parts[:2]) + "。"


def _join_fragments_en(opener: str, support: str, counter: str) -> str:
    parts = []
    for part in (opener, support, counter):
        normalized = str(part or "").strip().rstrip(".")
        if normalized and normalized not in parts:
            parts.append(normalized)
    if not parts:
        return "...Right."
    return ". ".join(parts[:2]) + "."
