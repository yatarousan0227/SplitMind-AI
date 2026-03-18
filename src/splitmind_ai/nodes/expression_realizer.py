"""ExpressionRealizerNode: realize one response from conflict outcome."""

from __future__ import annotations

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
        reads=["request", "persona", "relationship_state", "appraisal", "conflict_state", "mood", "conversation"],
        writes=["response", "trace"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=60,
                when={"conflict_state.ego_move.social_move": True},
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
        conversation = inputs.get_slice("conversation")
        response_language = str(request.get("response_language", "ja"))

        text, used_llm = await self._realize(
            user_message=str(request.get("user_message", "")),
            response_language=response_language,
            persona=persona,
            relationship_state=relationship_state,
            appraisal=appraisal,
            conflict_state=conflict_state,
            conversation=conversation,
        )
        trace = {
            "event_type": appraisal.get("event_type", ""),
            "ego_move": (conflict_state.get("ego_move") or {}).get("social_move", ""),
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
        conversation: dict[str, Any],
    ) -> tuple[str, bool]:
        fallback = _realize_text(
            response_language=response_language,
            persona=persona,
            relationship_state=relationship_state,
            appraisal=appraisal,
            conflict_state=conflict_state,
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
) -> str:
    event_type = str(appraisal.get("event_type") or "")
    move = str((conflict_state.get("ego_move") or {}).get("social_move") or "")
    residue = str((conflict_state.get("residue") or {}).get("visible_emotion") or "")
    trust = float(((relationship_state.get("durable") or {}).get("trust", 0.0)) or 0.0)

    if response_language == "en":
        return _realize_text_en(event_type, move, residue, trust)
    return _realize_text_ja(event_type, move, residue, trust)


def _realize_text_ja(event_type: str, move: str, residue: str, trust: float) -> str:
    if move == "accept_but_hold":
        if event_type == "repair_offer":
            return "うん、そこは受け取る。次はもう少しちゃんと言って。"
        return "受け取るよ。ただ、すぐに全部なかったことにはしない。"
    if move == "receive_without_chasing":
        return "そういう言い方をされると、少しだけ特別に聞こえる。…でも、こっちからは追わない。"
    if move == "allow_dependence_but_reframe":
        return "大丈夫。そういうふうに言ってくれるのは、ちゃんと嬉しい。"
    if move == "soft_tease_then_receive":
        return "へえ、楽しそうだったんだ。…まあ、それでも最後にこっちへ戻ってくるなら別にいいけど。"
    if move == "acknowledge_without_opening":
        if event_type == "distancing":
            return "そう。無理に引き止めはしない。ただ、軽く決めた言葉には聞こえなかった。"
        return "気持ちは分かった。今すぐ同じ温度で返すつもりはないけど。"
    if "warm" in residue or trust > 0.6:
        return "ちゃんと聞いてる。少しずつでいいなら、こっちも向き合う。"
    return "……そう。続けるなら、もう少し丁寧に話して。"


def _realize_text_en(event_type: str, move: str, residue: str, trust: float) -> str:
    if move == "accept_but_hold":
        if event_type == "repair_offer":
            return "Okay. I’ll take that. Just say it properly next time."
        return "I’ll take it, but I’m not going to act like nothing happened."
    if move == "receive_without_chasing":
        return "When you put it like that, it sounds a little too special. ...I’m not chasing it, though."
    if move == "allow_dependence_but_reframe":
        return "It’s fine. Hearing that still matters to me."
    if move == "soft_tease_then_receive":
        return "Oh, so you had fun. ...Fine, as long as you still drift back here."
    if move == "acknowledge_without_opening":
        if event_type == "distancing":
            return "I see. I’m not going to force you to stay, but that didn’t sound light either."
        return "I heard you. I’m not answering with the same temperature right away."
    if "warm" in residue or trust > 0.6:
        return "I’m listening. If slow is okay, I can meet you there."
    return "...Right. If you want to keep talking, do it a little more honestly."
