"""Graph builder and registry for next-generation SplitMind-AI."""

from __future__ import annotations

import logging
from typing import Any

from agent_contracts import build_graph_from_registry, get_node_registry, reset_registry
from agent_contracts.supervisor import GenericSupervisor
from langchain_core.language_models import BaseChatModel

from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.nodes.appraisal import AppraisalNode
from splitmind_ai.nodes.conflict_engine import ConflictEngineNode
from splitmind_ai.nodes.error_handler import ErrorNode
from splitmind_ai.nodes.expression_realizer import ExpressionRealizerNode
from splitmind_ai.nodes.fidelity_gate import FidelityGateNode
from splitmind_ai.nodes.memory_interpreter import MemoryInterpreterNode
from splitmind_ai.nodes.memory_commit import MemoryCommitNode
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode
from splitmind_ai.state.agent_state import CUSTOM_SLICES, SplitMindAgentState

logger = logging.getLogger(__name__)


def register_all_nodes(persona_name: str = "cold_attached_idol") -> None:
    """Register all active SplitMind nodes in the global registry."""
    registry = get_node_registry()

    for slice_name in CUSTOM_SLICES:
        registry.add_valid_slice(slice_name)

    registry.register(SessionBootstrapNode)
    registry.register(AppraisalNode)
    registry.register(ConflictEngineNode)
    registry.register(ExpressionRealizerNode)
    registry.register(FidelityGateNode)
    registry.register(MemoryInterpreterNode)
    registry.register(MemoryCommitNode)
    registry.register(ErrorNode)


def build_splitmind_graph(
    llm: BaseChatModel,
    persona_name: str = "cold_attached_idol",
    vault_path: str | None = None,
    max_iterations: int | None = None,
) -> Any:
    """Build and return a compiled LangGraph for SplitMind-AI."""
    reset_registry()
    register_all_nodes(persona_name=persona_name)

    vault_store = VaultStore(vault_path) if vault_path else None
    logger.debug(
        "Building SplitMind graph persona=%s vault_path=%s llm=%s",
        persona_name,
        vault_path,
        type(llm).__name__ if llm is not None else None,
    )

    graph = build_graph_from_registry(
        registry=get_node_registry(),
        llm=None,
        llm_provider=(lambda: llm) if llm is not None else None,
        supervisors=["main"],
        supervisor_factory=lambda name, _llm: GenericSupervisor(
            supervisor_name=name,
            llm=None,
            registry=get_node_registry(),
            max_iterations=max_iterations,
        ),
        state_class=SplitMindAgentState,
        dependency_provider=lambda contract: _provide_dependencies(contract, persona_name, vault_store),
    )

    graph.set_entry_point("main_supervisor")
    return graph.compile()


def _provide_dependencies(
    contract: Any,
    persona_name: str,
    vault_store: VaultStore | None,
) -> dict[str, Any]:
    """Provide node-specific dependencies based on the contract."""
    logger.debug("Providing dependencies for node=%s", contract.name)
    if contract.name == "session_bootstrap":
        return {"persona_name": persona_name, "vault_store": vault_store}
    if contract.name == "memory_commit":
        return {"vault_store": vault_store}
    return {}
