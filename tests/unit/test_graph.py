"""Tests for graph building and contract validation."""

from unittest.mock import MagicMock
import pytest

from agent_contracts import ContractValidator, get_node_registry, reset_registry

from splitmind_ai.app import graph as graph_module
from splitmind_ai.app.graph import build_splitmind_graph, register_all_nodes


def test_register_all_nodes():
    reset_registry()
    register_all_nodes()
    registry = get_node_registry()

    expected = {
        "session_bootstrap",
        "internal_dynamics",
        "motivational_state",
        "social_cue",
        "appraisal",
        "action_arbitration",
        "persona_supervisor",
        "utterance_planner",
        "surface_realization",
        "memory_commit",
        "error_handler",
    }
    assert set(registry.get_all_nodes()) == expected


def test_contract_validation_passes():
    reset_registry()
    register_all_nodes()
    registry = get_node_registry()

    validator = ContractValidator(registry=registry)
    result = validator.validate()
    assert not result.has_errors, f"Validation errors: {result.errors}"


def test_contract_reads_writes_consistency():
    """Verify the read/write matrix matches the implementation plan."""
    reset_registry()
    register_all_nodes()
    registry = get_node_registry()

    # SessionBootstrapNode
    c = registry.get_contract("session_bootstrap")
    assert "request" in c.reads
    assert "_internal" in c.reads
    assert "persona" in c.writes
    assert "relationship" in c.writes

    # InternalDynamicsNode
    c = registry.get_contract("internal_dynamics")
    assert "request" in c.reads
    assert "persona" in c.reads
    assert "dynamics" in c.writes
    assert "trace" in c.writes

    c = registry.get_contract("motivational_state")
    assert "dynamics" in c.reads
    assert "drive_state" in c.writes
    assert "inhibition_state" in c.writes

    c = registry.get_contract("social_cue")
    assert "drive_state" in c.reads
    assert "appraisal" in c.writes

    c = registry.get_contract("appraisal")
    assert "appraisal" in c.reads
    assert "drive_state" in c.reads
    assert "social_model" in c.writes
    assert "self_state" in c.writes

    c = registry.get_contract("action_arbitration")
    assert "appraisal" in c.reads
    assert "drive_state" in c.reads
    assert "conversation_policy" in c.writes

    # PersonaSupervisorNode
    c = registry.get_contract("persona_supervisor")
    assert "dynamics" in c.reads
    assert "conversation_policy" in c.reads
    assert "utterance_plan" in c.writes

    c = registry.get_contract("utterance_planner")
    assert "utterance_plan" in c.reads
    assert "utterance_plan" in c.writes

    c = registry.get_contract("surface_realization")
    assert "utterance_plan" in c.reads
    assert "drive_state" in c.reads
    assert "response" in c.writes

    # MemoryCommitNode
    c = registry.get_contract("memory_commit")
    assert "response" in c.reads
    assert "relationship" in c.writes
    assert "mood" in c.writes
    assert c.is_terminal is True

    # ErrorNode
    c = registry.get_contract("error_handler")
    assert "_internal" in c.reads
    assert "response" in c.writes
    assert c.is_terminal is True


def test_graph_builds_successfully():
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    compiled = build_splitmind_graph(llm=mock_llm)
    assert compiled is not None


def test_build_splitmind_graph_passes_llm_provider_with_dependency_provider(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class FakeGraph:
        def set_entry_point(self, entry_point: str) -> None:
            captured["entry_point"] = entry_point

        def compile(self):
            return "compiled"

    def fake_build_graph_from_registry(**kwargs):
        captured.update(kwargs)
        return FakeGraph()

    monkeypatch.setattr(graph_module, "build_graph_from_registry", fake_build_graph_from_registry)

    mock_llm = MagicMock()
    compiled = build_splitmind_graph(llm=mock_llm)

    assert compiled == "compiled"
    assert captured["llm"] is None
    assert captured["llm_provider"] is not None
    assert captured["llm_provider"]() is mock_llm
    assert captured["supervisor_factory"] is not None
    # supervisor_factory は LLM を無視して llm=None で GenericSupervisor を生成する
    from agent_contracts.supervisor import GenericSupervisor
    sv = captured["supervisor_factory"]("main", MagicMock())
    assert isinstance(sv, GenericSupervisor)
    assert sv.llm is None
    assert captured["entry_point"] == "main_supervisor"


def test_trigger_progression_prevents_internal_dynamics_loop():
    reset_registry()
    register_all_nodes()
    registry = get_node_registry()

    initial_state = {
        "request": {"user_message": "こんにちは"},
        "response": {},
        "_internal": {"is_first_turn": False},
    }
    matches = registry.evaluate_triggers("main", initial_state)
    assert [m.node_name for m in matches] == ["internal_dynamics"]

    after_dynamics = {
        **initial_state,
        "dynamics": {"id_output": {"drive_axes": [{"name": "curiosity_approach", "value": 0.3}]}},
    }
    matches = registry.evaluate_triggers("main", after_dynamics)
    assert [m.node_name for m in matches] == ["motivational_state"]

    after_motivational = {
        **after_dynamics,
        "drive_state": {"top_drives": [{"name": "curiosity_approach", "value": 0.3}]},
    }
    matches = registry.evaluate_triggers("main", after_motivational)
    assert [m.node_name for m in matches] == ["social_cue"]

    after_social_cue = {
        **after_motivational,
        "appraisal": {"social_cues": [{"cue_type": "ambiguity"}]},
    }
    matches = registry.evaluate_triggers("main", after_social_cue)
    assert [m.node_name for m in matches] == ["appraisal"]

    after_appraisal = {
        **after_social_cue,
        "appraisal": {
            "social_cues": [{"cue_type": "ambiguity"}],
            "dominant_appraisal": "uncertain",
        },
    }
    matches = registry.evaluate_triggers("main", after_appraisal)
    assert [m.node_name for m in matches] == ["action_arbitration"]

    after_policy = {
        **after_appraisal,
        "conversation_policy": {"selected_mode": "deflect"},
    }
    matches = registry.evaluate_triggers("main", after_policy)
    assert [m.node_name for m in matches] == ["persona_supervisor"]

    after_frame = {
        **after_policy,
        "utterance_plan": {"surface_intent": "hold distance"},
    }
    matches = registry.evaluate_triggers("main", after_frame)
    assert [m.node_name for m in matches] == ["utterance_planner"]

    after_candidates = {
        **after_frame,
        "utterance_plan": {
            "surface_intent": "hold distance",
            "candidates": [
                {"label": "a", "mode": "deflect"},
                {"label": "b", "mode": "withdraw"},
            ],
        },
    }
    matches = registry.evaluate_triggers("main", after_candidates)
    assert [m.node_name for m in matches] == ["surface_realization"]

    after_response = {
        **after_candidates,
        "response": {"final_response_text": "...うん。"},
    }
    matches = registry.evaluate_triggers("main", after_response)
    assert [m.node_name for m in matches] == ["memory_commit"]
