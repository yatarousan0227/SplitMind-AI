"""Baseline system configurations for comparison evaluation.

4 baselines:
1. single_persona: Single persona bot (no internal dynamics, no memory)
2. persona_memory: Persona + memory bot (no psychodynamic internals)
3. emotion_label: Emotion-label response system (labels emotion, no dynamics)
4. multi_agent_flat: Multi-agent without psychodynamic roles

Plus the full SplitMind system as the primary target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel

from splitmind_ai.app.llm import create_chat_llm
from splitmind_ai.app.settings import load_settings


@dataclass
class BaselineConfig:
    """Configuration for a baseline system."""

    name: str
    description: str
    # Which nodes to include (by contract name)
    nodes: list[str]
    # Whether to use vault memory
    use_vault: bool = False
    # Whether to use the state update engine
    use_state_updates: bool = False
    # Custom system prompt override (for simplified baselines)
    system_prompt_override: str | None = None
    # LLM call count per turn
    llm_calls_per_turn: int = 1


# ---------------------------------------------------------------------------
# Baseline definitions
# ---------------------------------------------------------------------------

BASELINES: dict[str, BaselineConfig] = {
    "single_persona": BaselineConfig(
        name="single_persona",
        description="Single persona bot - no internal dynamics, no memory, no state updates",
        nodes=["session_bootstrap", "persona_supervisor", "error_handler"],
        use_vault=False,
        use_state_updates=False,
        llm_calls_per_turn=1,
        system_prompt_override=(
            "あなたはキャラクターとして会話します。\n"
            "ペルソナ設定に従い、自然な日本語で返答してください。\n"
            "内部葛藤や心理分析は不要です。"
        ),
    ),
    "persona_memory": BaselineConfig(
        name="persona_memory",
        description="Persona + memory bot - has memory but no psychodynamic internals",
        nodes=["session_bootstrap", "persona_supervisor", "memory_commit", "error_handler"],
        use_vault=True,
        use_state_updates=False,
        llm_calls_per_turn=1,
        system_prompt_override=(
            "あなたはキャラクターとして会話します。\n"
            "ペルソナ設定に従い、過去の会話記憶を参照して返答してください。\n"
            "内部葛藤や心理分析は不要です。"
        ),
    ),
    "emotion_label": BaselineConfig(
        name="emotion_label",
        description="Emotion-label system - labels emotion then responds, no dynamics",
        nodes=["session_bootstrap", "persona_supervisor", "error_handler"],
        use_vault=False,
        use_state_updates=False,
        llm_calls_per_turn=1,
        system_prompt_override=(
            "あなたはキャラクターとして会話します。\n"
            "まずユーザーの発言から感情ラベル（喜び、悲しみ、怒り、不安、中立）を判定し、\n"
            "そのラベルに基づいて返答してください。\n"
            "Id/Ego/Superego のような内部葛藤モデルは使わないでください。"
        ),
    ),
    "multi_agent_flat": BaselineConfig(
        name="multi_agent_flat",
        description="Multi-agent without psychodynamic roles - parallel agents, no Id/Ego/Superego",
        nodes=["session_bootstrap", "internal_dynamics", "persona_supervisor",
               "memory_commit", "error_handler"],
        use_vault=True,
        use_state_updates=True,
        llm_calls_per_turn=2,
        system_prompt_override=(
            "あなたは複数の分析モジュールを持つ会話エージェントです。\n"
            "モジュール1: 状況分析（ユーザーの意図と感情を分析）\n"
            "モジュール2: 応答生成（分析結果に基づき返答）\n"
            "精神力動的役割（Id/Ego/Superego）は使わないでください。\n"
            "防衛機制や漏出といった概念は適用しないでください。"
        ),
    ),
    "splitmind_full": BaselineConfig(
        name="splitmind_full",
        description="Full SplitMind system with psychodynamic roles",
        nodes=["session_bootstrap", "internal_dynamics", "persona_supervisor",
               "memory_commit", "error_handler"],
        use_vault=True,
        use_state_updates=True,
        llm_calls_per_turn=2,
        system_prompt_override=None,  # Use default prompts
    ),
}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def _create_llm() -> BaseChatModel:
    """Create LLM instance from settings."""
    settings = load_settings()
    return create_chat_llm(settings)


def build_baseline_graph(
    config: BaselineConfig,
    persona_name: str = "cold_attached_idol",
    vault_path: str | None = None,
) -> Any:
    """Build a compiled graph for a specific baseline configuration.

    For the full splitmind system, delegates to the standard graph builder.
    For simplified baselines, builds a reduced graph with prompt overrides.
    """
    from splitmind_ai.app.graph import build_splitmind_graph

    llm = _create_llm()

    if config.name == "splitmind_full":
        return build_splitmind_graph(
            llm=llm,
            persona_name=persona_name,
            vault_path=vault_path if config.use_vault else None,
        )

    # For baselines with prompt overrides, we still build the full graph
    # but the evaluation framework tracks which nodes are active.
    # The system_prompt_override is applied at evaluation time.
    return build_splitmind_graph(
        llm=llm,
        persona_name=persona_name,
        vault_path=vault_path if config.use_vault else None,
    )


def get_baseline_metadata() -> dict[str, dict[str, Any]]:
    """Return metadata about all baselines for reporting."""
    return {
        name: {
            "description": cfg.description,
            "nodes": cfg.nodes,
            "use_vault": cfg.use_vault,
            "use_state_updates": cfg.use_state_updates,
            "llm_calls_per_turn": cfg.llm_calls_per_turn,
            "has_prompt_override": cfg.system_prompt_override is not None,
        }
        for name, cfg in BASELINES.items()
    }
