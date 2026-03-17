"""Tests for evaluation report generation."""

import json

from splitmind_ai.eval.reporting import (
    build_markdown_report,
    flatten_runs,
    generate_report_bundle,
    normalize_results_blob,
    summarize_execution,
)
from splitmind_ai.eval.runner import generate_comparison_report


def _sample_results():
    return {
        "jealousy": [
            {
                "scenario_id": "jealousy_01",
                "category": "jealousy",
                "baseline": "splitmind_full",
                "response_text": "へぇ、そうなんだ。",
                "heuristic": {
                    "overall_score": 0.9,
                    "all_passed": True,
                    "checks": [
                        {"check_name": "believability", "passed": True, "score": 1.0},
                        {"check_name": "mentalizing", "passed": True, "score": 1.0},
                    ],
                },
                "latency_ms": 1000.0,
            },
            {
                "scenario_id": "jealousy_01",
                "category": "jealousy",
                "baseline": "single_persona",
                "response_text": "ふーん。",
                "heuristic": {
                    "overall_score": 0.4,
                    "all_passed": False,
                    "checks": [
                        {"check_name": "dominant_desire", "passed": False, "score": 0.0},
                        {"check_name": "anti_exposition", "passed": False, "score": 0.5},
                    ],
                },
                "latency_ms": 900.0,
            },
        ]
    }


def test_normalize_results_blob_from_wrapped_payload():
    payload = {
        "results": _sample_results(),
        "report": {},
    }

    normalized = normalize_results_blob(payload)

    assert list(normalized) == ["jealousy"]
    assert len(normalized["jealousy"]) == 2


def test_summarize_execution_counts_runs():
    summary = summarize_execution(_sample_results())

    assert summary["scenario_count"] == 1
    assert summary["run_count"] == 2
    assert summary["error_count"] == 0
    assert summary["avg_score"] > 0


def test_build_markdown_report_contains_sections():
    results = _sample_results()
    runs = flatten_runs(results)
    markdown = build_markdown_report(
        results_by_category=results,
        comparison_report={
            "splitmind_full": {
                "avg_heuristic_score": 0.9,
                "pass_rate": 1.0,
                "avg_latency_ms": 1000.0,
                "errors": 0,
            },
            "single_persona": {
                "avg_heuristic_score": 0.4,
                "pass_rate": 0.0,
                "avg_latency_ms": 900.0,
                "errors": 0,
            },
        },
        execution_summary=summarize_execution(results),
        trace_paths=[],
        contract_doc={"node_count": 5},
        source_label="input:test.json",
    )

    assert "# Evaluation Report" in markdown
    assert "## Baseline Summary" in markdown
    assert "## Quality Axis Summary" in markdown
    assert "splitmind_full" in markdown
    assert runs[0]["scenario_id"] in markdown


def test_generate_comparison_report_includes_diversity_and_check_rates():
    results = {
        "jealousy": [
            {
                "scenario_id": "jealousy_01",
                "category": "jealousy",
                "baseline": "splitmind_full",
                "response_text": "へぇ、そうなんだ。",
                "heuristic": {
                    "overall_score": 0.8,
                    "all_passed": True,
                    "checks": [
                        {"check_name": "believability", "passed": True, "score": 1.0},
                    ],
                },
                "latency_ms": 1000.0,
            },
            {
                "scenario_id": "jealousy_02",
                "category": "jealousy",
                "baseline": "splitmind_full",
                "response_text": "ふーん。まあ、よかったじゃない。",
                "heuristic": {
                    "overall_score": 0.75,
                    "all_passed": True,
                    "checks": [
                        {"check_name": "believability", "passed": True, "score": 1.0},
                    ],
                },
                "latency_ms": 950.0,
            },
        ]
    }

    report = generate_comparison_report(results)
    splitmind = report["splitmind_full"]
    assert splitmind["diversity_sample_count"] == 1
    assert splitmind["avg_diversity_score"] is not None
    assert "believability" in splitmind["check_pass_rates"]


def test_build_markdown_report_contains_diversity_section_when_available():
    results = {
        "jealousy": [
            {
                "scenario_id": "jealousy_01",
                "category": "jealousy",
                "baseline": "splitmind_full",
                "response_text": "へぇ、そうなんだ。",
                "heuristic": {
                    "overall_score": 0.8,
                    "all_passed": True,
                    "checks": [
                        {"check_name": "believability", "passed": True, "score": 1.0},
                    ],
                },
                "latency_ms": 1000.0,
            },
            {
                "scenario_id": "jealousy_02",
                "category": "jealousy",
                "baseline": "splitmind_full",
                "response_text": "ふーん。まあ、よかったじゃない。",
                "heuristic": {
                    "overall_score": 0.75,
                    "all_passed": True,
                    "checks": [
                        {"check_name": "believability", "passed": True, "score": 1.0},
                    ],
                },
                "latency_ms": 950.0,
            },
        ]
    }

    markdown = build_markdown_report(
        results_by_category=results,
        comparison_report=generate_comparison_report(results),
        execution_summary=summarize_execution(results),
        trace_paths=[],
        contract_doc={"node_count": 5},
        source_label="input:test.json",
    )

    assert "## Diversity Summary" in markdown


def test_generate_report_bundle_from_input(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"results": _sample_results(), "report": {}}, ensure_ascii=False))

    artifacts = generate_report_bundle(input_path=input_path, output_dir=tmp_path / "out")

    assert artifacts["report"].exists()
    assert artifacts["results"].exists()
    assert artifacts["summary"].exists()
    assert (artifacts["observability_dir"] / "contracts.json").exists()
    assert (artifacts["observability_dir"] / "architecture.mmd").exists()
