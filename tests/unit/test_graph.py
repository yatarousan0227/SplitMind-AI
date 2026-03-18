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
        "appraisal",
        "conflict_engine",
        "turn_shaping_policy",
        "expression_realizer",
        "fidelity_gate",
        "memory_interpreter",
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
    reset_registry()
    register_all_nodes()
    registry = get_node_registry()

    c = registry.get_contract("session_bootstrap")
    assert "request" in c.reads
    assert "persona" in c.writes
    assert "relationship_state" in c.writes

    c = registry.get_contract("appraisal")
    assert "request" in c.reads
    assert "persona" in c.reads
    assert "relationship_state" in c.reads
    assert "conversation" in c.reads
    assert "appraisal" in c.writes
    assert c.requires_llm is True

    c = registry.get_contract("conflict_engine")
    assert "persona" in c.reads
    assert "appraisal" in c.reads
    assert "relationship_state" in c.reads
    assert "conversation" in c.reads
    assert "conflict_state" in c.writes
    assert c.requires_llm is True

    c = registry.get_contract("turn_shaping_policy")
    assert "appraisal" in c.reads
    assert "conflict_state" in c.reads
    assert "turn_shaping_policy" in c.writes
    assert "repair_policy" in c.writes
    assert "comparison_policy" in c.writes

    c = registry.get_contract("expression_realizer")
    assert "conflict_state" in c.reads
    assert "conversation" in c.reads
    assert "response" in c.writes
    assert c.requires_llm is True

    c = registry.get_contract("fidelity_gate")
    assert "response" in c.reads
    assert "conversation" in c.reads
    assert "trace" in c.writes
    assert c.requires_llm is True

    c = registry.get_contract("memory_interpreter")
    assert "response" in c.reads
    assert "working_memory" in c.reads
    assert "memory_interpretation" in c.writes
    assert c.requires_llm is True

    c = registry.get_contract("memory_commit")
    assert "trace" in c.reads
    assert "memory_interpretation" in c.reads
    assert "relationship_state" in c.reads
    assert "relationship_state" in c.writes
    assert c.is_terminal is True

    c = registry.get_contract("error_handler")
    assert "_internal" in c.reads
    assert "response" in c.writes
    assert c.is_terminal is True


def test_graph_builds_successfully():
    mock_llm = MagicMock()
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
    compiled = build_splitmind_graph(llm=mock_llm, max_iterations=17)

    assert compiled == "compiled"
    assert captured["llm"] is None
    assert captured["llm_provider"] is not None
    assert captured["llm_provider"]() is mock_llm
    from agent_contracts.supervisor import GenericSupervisor
    sv = captured["supervisor_factory"]("main", MagicMock())
    assert isinstance(sv, GenericSupervisor)
    assert sv.llm is None
    assert sv.max_iterations == 17
    assert captured["entry_point"] == "main_supervisor"


def test_trigger_progression_matches_new_pipeline():
    reset_registry()
    register_all_nodes()
    registry = get_node_registry()

    initial_state = {
        "request": {"user_message": "こんにちは"},
        "response": {},
        "_internal": {"is_first_turn": False},
    }
    matches = registry.evaluate_triggers("main", initial_state)
    assert [m.node_name for m in matches] == ["appraisal"]

    after_appraisal = {
        **initial_state,
        "appraisal": {"event_type": "ambiguity"},
    }
    matches = registry.evaluate_triggers("main", after_appraisal)
    assert [m.node_name for m in matches] == ["conflict_engine"]

    after_conflict = {
        **after_appraisal,
        "conflict_state": {"ego_move": {"move_family": "affection_receipt", "move_style": "defer_without_chasing"}},
    }
    matches = registry.evaluate_triggers("main", after_conflict)
    assert [m.node_name for m in matches] == ["turn_shaping_policy"]

    after_policy = {
        **after_conflict,
        "turn_shaping_policy": {"primary_frame": "affection_receipt"},
        "repair_policy": {"repair_mode": "closed"},
        "comparison_policy": {"comparison_threat_level": 0.0},
        "trace": {
            "turn_shaping_policy": {"primary_frame": "affection_receipt"},
            "repair_policy": {"repair_mode": "closed"},
            "comparison_policy": {"comparison_threat_level": 0.0},
        },
    }
    matches = registry.evaluate_triggers("main", after_policy)
    assert [m.node_name for m in matches] == ["expression_realizer"]

    after_response = {
        **after_policy,
        "response": {"final_response_text": "...うん。"},
    }
    matches = registry.evaluate_triggers("main", after_response)
    assert [m.node_name for m in matches] == ["fidelity_gate"]

    after_gate = {
        **after_response,
        "trace": {
            "turn_shaping_policy": {"primary_frame": "affection_receipt"},
            "repair_policy": {"repair_mode": "closed"},
            "comparison_policy": {"comparison_threat_level": 0.0},
            "fidelity_gate": {"passed": True},
        },
    }
    matches = registry.evaluate_triggers("main", after_gate)
    assert [m.node_name for m in matches] == ["memory_interpreter"]

    after_memory_interpreter = {
        **after_gate,
        "trace": {
            "turn_shaping_policy": {"primary_frame": "affection_receipt"},
            "repair_policy": {"repair_mode": "closed"},
            "comparison_policy": {"comparison_threat_level": 0.0},
            "fidelity_gate": {"passed": True},
            "memory_interpreter": {"used_llm": True},
        },
        "memory_interpretation": {"event_flags": {"repair_attempt": True}},
    }
    matches = registry.evaluate_triggers("main", after_memory_interpreter)
    assert [m.node_name for m in matches] == ["memory_commit"]
