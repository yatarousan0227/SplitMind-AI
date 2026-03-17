"""Tests for observability utilities."""

import json
from pathlib import Path

import pytest

from splitmind_ai.eval.observability import (
    diff_contracts,
    load_traces,
    save_scenario_trace,
)


class TestTraceExport:
    def test_save_and_load(self, tmp_path):
        result = {
            "response_text": "test",
            "heuristic": {"score": 0.8},
        }
        path = save_scenario_trace(
            "test_01", "splitmind_full", result, output_dir=tmp_path
        )
        assert path.exists()

        traces = load_traces(traces_dir=tmp_path)
        assert len(traces) == 1
        assert traces[0]["scenario_id"] == "test_01"
        assert traces[0]["baseline"] == "splitmind_full"

    def test_filter_by_scenario(self, tmp_path):
        save_scenario_trace("s1", "b1", {"x": 1}, output_dir=tmp_path)
        save_scenario_trace("s2", "b1", {"x": 2}, output_dir=tmp_path)

        traces = load_traces(scenario_id="s1", traces_dir=tmp_path)
        assert len(traces) == 1
        assert traces[0]["scenario_id"] == "s1"

    def test_filter_by_baseline(self, tmp_path):
        save_scenario_trace("s1", "b1", {"x": 1}, output_dir=tmp_path)
        save_scenario_trace("s1", "b2", {"x": 2}, output_dir=tmp_path)

        traces = load_traces(baseline="b2", traces_dir=tmp_path)
        assert len(traces) == 1
        assert traces[0]["baseline"] == "b2"

    def test_load_empty_dir(self, tmp_path):
        traces = load_traces(traces_dir=tmp_path)
        assert traces == []

    def test_load_nonexistent_dir(self, tmp_path):
        traces = load_traces(traces_dir=tmp_path / "nonexistent")
        assert traces == []


class TestContractDiff:
    def test_no_changes(self):
        doc = {"nodes": [{"name": "a", "reads": ["x"], "writes": ["y"],
                          "is_terminal": False, "triggers": []}]}
        diff = diff_contracts(doc, doc)
        assert diff["has_changes"] is False
        assert diff["added_nodes"] == []
        assert diff["removed_nodes"] == []
        assert diff["changed_nodes"] == []

    def test_added_node(self):
        old = {"nodes": [{"name": "a", "reads": [], "writes": [],
                          "is_terminal": False, "triggers": []}]}
        new = {"nodes": [
            {"name": "a", "reads": [], "writes": [], "is_terminal": False, "triggers": []},
            {"name": "b", "reads": ["x"], "writes": ["y"], "is_terminal": False, "triggers": []},
        ]}
        diff = diff_contracts(old, new)
        assert diff["has_changes"] is True
        assert len(diff["added_nodes"]) == 1
        assert diff["added_nodes"][0]["name"] == "b"

    def test_removed_node(self):
        old = {"nodes": [
            {"name": "a", "reads": [], "writes": [], "is_terminal": False, "triggers": []},
            {"name": "b", "reads": [], "writes": [], "is_terminal": False, "triggers": []},
        ]}
        new = {"nodes": [{"name": "a", "reads": [], "writes": [],
                          "is_terminal": False, "triggers": []}]}
        diff = diff_contracts(old, new)
        assert diff["has_changes"] is True
        assert len(diff["removed_nodes"]) == 1
        assert diff["removed_nodes"][0]["name"] == "b"

    def test_changed_node(self):
        old = {"nodes": [{"name": "a", "reads": ["x"], "writes": ["y"],
                          "is_terminal": False, "triggers": []}]}
        new = {"nodes": [{"name": "a", "reads": ["x", "z"], "writes": ["y"],
                          "is_terminal": False, "triggers": []}]}
        diff = diff_contracts(old, new)
        assert diff["has_changes"] is True
        assert len(diff["changed_nodes"]) == 1
        assert "reads" in diff["changed_nodes"][0]["changes"]
