"""Baseline configurations aligned to the next-generation runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel

from splitmind_ai.app.graph import build_splitmind_graph
from splitmind_ai.app.llm import create_chat_llm
from splitmind_ai.app.settings import load_settings


@dataclass
class BaselineConfig:
    """Configuration for an evaluation baseline."""

    name: str
    description: str
    kind: str  # graph | single_prompt
    use_vault: bool = False
    llm_calls_per_turn: int = 1
    persona_format: str | None = None
    include_summary_memo: bool = False


BASELINES: dict[str, BaselineConfig] = {
    "splitmind_full": BaselineConfig(
        name="splitmind_full",
        description="Full conflict-engine runtime with appraisal, conflict, fidelity, and memory",
        kind="graph",
        use_vault=True,
        llm_calls_per_turn=2,
    ),
    "single_prompt_dedicated": BaselineConfig(
        name="single_prompt_dedicated",
        description="Single-prompt persona baseline using hand-authored dedicated prompts per persona",
        kind="single_prompt",
        use_vault=False,
        llm_calls_per_turn=1,
        persona_format="dedicated",
        include_summary_memo=False,
    ),
    "single_prompt_compact": BaselineConfig(
        name="single_prompt_compact",
        description="Single-prompt persona baseline using compact v2 persona serialization",
        kind="single_prompt",
        use_vault=False,
        llm_calls_per_turn=1,
        persona_format="compact",
        include_summary_memo=False,
    ),
}


def _create_llm() -> BaseChatModel:
    settings = load_settings()
    return create_chat_llm(settings)


def build_baseline_graph(
    config: BaselineConfig,
    persona_name: str = "cold_attached_idol",
    vault_path: str | None = None,
) -> Any:
    """Build a compiled graph for graph-based baselines."""
    if config.kind != "graph":
        raise ValueError(f"Baseline {config.name} is not graph-based")
    settings = load_settings()
    llm = _create_llm()
    return build_splitmind_graph(
        llm=llm,
        persona_name=persona_name,
        vault_path=vault_path if config.use_vault else None,
        max_iterations=settings.runtime.max_iterations,
    )


def get_baseline_metadata() -> dict[str, dict[str, Any]]:
    """Return metadata about all baselines for reporting."""
    return {
        name: {
            "description": cfg.description,
            "kind": cfg.kind,
            "use_vault": cfg.use_vault,
            "llm_calls_per_turn": cfg.llm_calls_per_turn,
            "persona_format": cfg.persona_format,
            "include_summary_memo": cfg.include_summary_memo,
        }
        for name, cfg in BASELINES.items()
    }
