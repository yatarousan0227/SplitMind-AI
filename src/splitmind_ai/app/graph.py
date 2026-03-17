"""Graph builder and registry for SplitMind-AI.

Registers all nodes, configures the graph, and provides a build function.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_contracts import (
    build_graph_from_registry,
    get_node_registry,
    reset_registry,
)
from agent_contracts.supervisor import GenericSupervisor
from langchain_core.language_models import BaseChatModel

from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.nodes.action_arbitration import ActionArbitrationNode
from splitmind_ai.nodes.appraisal import AppraisalNode
from splitmind_ai.nodes.error_handler import ErrorNode
from splitmind_ai.nodes.internal_dynamics import InternalDynamicsNode
from splitmind_ai.nodes.memory_commit import MemoryCommitNode
from splitmind_ai.nodes.motivational_state import MotivationalStateNode
from splitmind_ai.nodes.persona_supervisor import PersonaSupervisorNode
from splitmind_ai.nodes.surface_realization import SurfaceRealizationNode
from splitmind_ai.nodes.session_bootstrap import SessionBootstrapNode
from splitmind_ai.nodes.social_cue import SocialCueNode
from splitmind_ai.nodes.utterance_planner import UtterancePlannerNode
from splitmind_ai.state.agent_state import CUSTOM_SLICES, SplitMindAgentState

logger = logging.getLogger(__name__)


def register_all_nodes(persona_name: str = "cold_attached_idol") -> None:
    """Register all SplitMind nodes in the global registry.

    This must be called before building the graph.
    """
    registry = get_node_registry()

    # Register custom slices
    for slice_name in CUSTOM_SLICES:
        registry.add_valid_slice(slice_name)

    # Register nodes
    registry.register(SessionBootstrapNode)
    registry.register(InternalDynamicsNode)
    registry.register(MotivationalStateNode)
    registry.register(SocialCueNode)
    registry.register(AppraisalNode)
    registry.register(ActionArbitrationNode)
    registry.register(PersonaSupervisorNode)
    registry.register(UtterancePlannerNode)
    registry.register(SurfaceRealizationNode)
    registry.register(MemoryCommitNode)
    registry.register(ErrorNode)


def build_splitmind_graph(
    llm: BaseChatModel,
    persona_name: str = "cold_attached_idol",
    vault_path: str | None = None,
) -> Any:
    """Build and return a compiled LangGraph for SplitMind-AI.

    Args:
        llm: The LangChain chat model to use for LLM-dependent nodes.
        persona_name: Name of the persona config to load.
        vault_path: Path to Obsidian vault. None disables vault persistence.

    Returns:
        A compiled LangGraph StateGraph ready for invocation.
    """
    reset_registry()
    register_all_nodes(persona_name=persona_name)

    vault_store = VaultStore(vault_path) if vault_path else None
    registry = get_node_registry()
    logger.debug(
        "Building SplitMind graph persona=%s vault_path=%s llm=%s",
        persona_name,
        vault_path,
        type(llm).__name__ if llm is not None else None,
    )

    graph = build_graph_from_registry(
        registry=registry,
        llm=None,
        llm_provider=(lambda: llm) if llm is not None else None,
        supervisors=["main"],
        supervisor_factory=lambda name, _llm: GenericSupervisor(
            supervisor_name=name,
            llm=None,
            registry=get_node_registry(),
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
