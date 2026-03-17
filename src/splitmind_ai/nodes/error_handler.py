"""ErrorNode: handle contract violations and LLM parse failures.

Reads: _internal.errors, request, dynamics, response
Writes: response, trace.error, _internal.status
Trigger: contract violation or node failure (high priority)
"""

from __future__ import annotations

from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition


class ErrorNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="error_handler",
        description="Handle contract violations and LLM failures with safe fallback",
        reads=["request", "dynamics", "response", "_internal"],
        writes=["response", "trace", "_internal"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"_internal.error": True},
                llm_hint="Activate when an error occurs in the pipeline",
            ),
        ],
        is_terminal=True,
        icon="⚠️",
    )

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        internal = inputs.get_slice("_internal")
        request = inputs.get_slice("request")
        response_language = request.get("response_language", "ja")

        error_msg = internal.get("error", "Unknown error")
        errors_list = internal.get("errors", [])
        fallback_text = (
            "...Sorry, I couldn't get my thoughts to come together."
            if response_language == "en"
            else "...ごめん、ちょっとうまく考えがまとまらなかった。"
        )

        # Build a safe fallback response
        response = {
            "response_type": "error",
            "response_data": {
                "error": error_msg,
                "errors": errors_list,
            },
            "response_message": fallback_text,
            "final_response_text": fallback_text,
        }

        trace = {
            "error": {
                "error_message": error_msg,
                "errors_count": len(errors_list),
                "user_message": request.get("user_message", ""),
            }
        }

        return NodeOutputs(
            response=response,
            trace=trace,
            _internal={"status": "error_handled"},
        )
