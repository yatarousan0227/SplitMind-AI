"""High-level evaluation reporting script.

Aggregates evaluation results into a readable Markdown report and
emits observability artifacts in one place.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from splitmind_ai.app.logging_utils import configure_logging
from splitmind_ai.eval.baselines import get_baseline_metadata
from splitmind_ai.eval.observability import generate_contract_docs, save_scenario_trace
from splitmind_ai.eval.runner import generate_comparison_report, run_all, run_category

REPORTS_DIR = Path(__file__).parent / "reports"


def normalize_results_blob(data: Any) -> dict[str, list[dict[str, Any]]]:
    """Normalize runner output or saved JSON into {category: runs} form."""
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        if isinstance(results, dict):
            return {str(k): list(v) for k, v in results.items()}
        raise TypeError("Expected 'results' to be a category map")

    if isinstance(data, dict):
        if all(isinstance(v, list) for v in data.values()):
            return {str(k): list(v) for k, v in data.items()}
        raise TypeError("Unsupported results mapping format")

    if isinstance(data, list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for run in data:
            category = run.get("category", "unknown")
            grouped.setdefault(category, []).append(run)
        return grouped

    raise TypeError(f"Unsupported results blob type: {type(data)!r}")


def flatten_runs(results_by_category: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Flatten category-keyed results."""
    runs: list[dict[str, Any]] = []
    for category in sorted(results_by_category):
        runs.extend(results_by_category[category])
    return runs


def summarize_execution(results_by_category: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Build a compact execution summary."""
    runs = flatten_runs(results_by_category)
    valid_runs = [run for run in runs if "error" not in run]
    error_runs = [run for run in runs if "error" in run]
    baselines = sorted({run.get("baseline", "unknown") for run in runs})
    categories = sorted(results_by_category)
    scenarios = sorted({run.get("scenario_id", "unknown") for run in runs})

    avg_score = (
        sum(run.get("heuristic", {}).get("overall_score", 0.0) for run in valid_runs) / len(valid_runs)
        if valid_runs else 0.0
    )
    avg_structural_score = (
        sum(run.get("heuristic", {}).get("structural_score", 0.0) for run in valid_runs) / len(valid_runs)
        if valid_runs else 0.0
    )
    avg_latency = (
        sum(run.get("latency_ms", 0.0) for run in valid_runs) / len(valid_runs)
        if valid_runs else 0.0
    )

    category_summary: list[dict[str, Any]] = []
    for category in categories:
        category_runs = results_by_category[category]
        category_valid = [run for run in category_runs if "error" not in run]
        category_summary.append({
            "category": category,
            "runs": len(category_runs),
            "errors": sum(1 for run in category_runs if "error" in run),
            "avg_score": (
                sum(run.get("heuristic", {}).get("overall_score", 0.0) for run in category_valid) / len(category_valid)
                if category_valid else 0.0
            ),
            "avg_structural_score": (
                sum(run.get("heuristic", {}).get("structural_score", 0.0) for run in category_valid) / len(category_valid)
                if category_valid else 0.0
            ),
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "categories": categories,
        "baselines": baselines,
        "scenario_count": len(scenarios),
        "run_count": len(runs),
        "valid_run_count": len(valid_runs),
        "error_count": len(error_runs),
        "avg_score": avg_score,
        "avg_structural_score": avg_structural_score,
        "avg_latency_ms": avg_latency,
        "category_summary": category_summary,
    }


def _collect_failed_checks(run: dict[str, Any]) -> list[str]:
    checks = run.get("heuristic", {}).get("checks", [])
    return [check.get("check_name", "unknown") for check in checks if not check.get("passed", False)]


def _top_runs(
    runs: list[dict[str, Any]],
    *,
    reverse: bool,
    limit: int = 5,
) -> list[dict[str, Any]]:
    valid_runs = [run for run in runs if "error" not in run]
    return sorted(
        valid_runs,
        key=lambda run: run.get("heuristic", {}).get("overall_score", 0.0),
        reverse=reverse,
    )[:limit]


def summarize_check_metrics(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate heuristic checks across valid runs."""
    metrics: dict[str, dict[str, float]] = {}
    for run in runs:
        if "error" in run:
            continue
        for check in run.get("heuristic", {}).get("checks", []):
            name = check.get("check_name", "unknown")
            bucket = metrics.setdefault(name, {"total": 0, "passed": 0, "score_sum": 0.0})
            bucket["total"] += 1
            bucket["passed"] += 1 if check.get("passed", False) else 0
            bucket["score_sum"] += float(check.get("score", 0.0))

    summary: list[dict[str, Any]] = []
    for name, bucket in sorted(metrics.items()):
        total = int(bucket["total"])
        summary.append({
            "check_name": name,
            "count": total,
            "pass_rate": bucket["passed"] / total if total > 0 else 0.0,
            "avg_score": bucket["score_sum"] / total if total > 0 else 0.0,
        })
    return summary


def _save_run_traces(runs: list[dict[str, Any]], traces_dir: Path) -> list[Path]:
    traces_dir.mkdir(parents=True, exist_ok=True)
    trace_paths: list[Path] = []
    for run in runs:
        if "error" in run:
            continue
        trace_paths.append(
            save_scenario_trace(
                scenario_id=run.get("scenario_id", "unknown"),
                baseline=run.get("baseline", "unknown"),
                result=run,
                output_dir=traces_dir,
            )
        )
    return trace_paths


def build_markdown_report(
    *,
    results_by_category: dict[str, list[dict[str, Any]]],
    comparison_report: dict[str, Any],
    execution_summary: dict[str, Any],
    trace_paths: list[Path],
    contract_doc: dict[str, Any],
    source_label: str,
) -> str:
    """Render a readable Markdown report."""
    runs = flatten_runs(results_by_category)
    baseline_meta = get_baseline_metadata()
    best_baseline = max(
        comparison_report.items(),
        key=lambda item: item[1].get("avg_heuristic_score", 0.0),
        default=None,
    )
    fastest_baseline = min(
        comparison_report.items(),
        key=lambda item: item[1].get("avg_latency_ms", float("inf")),
        default=None,
    )
    failing_runs = [run for run in runs if "error" in run or not run.get("heuristic", {}).get("all_passed", False)]
    top_runs = _top_runs(runs, reverse=True)
    bottom_runs = _top_runs(runs, reverse=False)

    lines = [
        "# Evaluation Report",
        "",
        f"- Generated: {execution_summary['generated_at']}",
        f"- Source: {source_label}",
        f"- Categories: {', '.join(execution_summary['categories']) or '(none)'}",
        f"- Baselines: {', '.join(execution_summary['baselines']) or '(none)'}",
        "",
        "## Execution Summary",
        "",
        f"- Scenarios: {execution_summary['scenario_count']}",
        f"- Runs: {execution_summary['run_count']}",
        f"- Valid runs: {execution_summary['valid_run_count']}",
        f"- Errors: {execution_summary['error_count']}",
        f"- Average heuristic score: {execution_summary['avg_score']:.3f}",
        f"- Average structural score: {execution_summary['avg_structural_score']:.3f}",
        f"- Average latency: {execution_summary['avg_latency_ms']:.1f} ms",
        "",
        "## Baseline Summary",
        "",
        "| Baseline | Avg Score | Structural | Pass Rate | Avg Latency (ms) | Avg Diversity | Errors | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for baseline, stats in sorted(comparison_report.items()):
        notes = baseline_meta.get(baseline, {}).get("description", "")
        diversity_value = stats.get("avg_diversity_score")
        diversity_label = f"{diversity_value:.3f}" if isinstance(diversity_value, float) else "-"
        lines.append(
            f"| {baseline} | {stats['avg_heuristic_score']:.3f} | "
            f"{stats.get('avg_structural_score', 0.0):.3f} | "
            f"{stats['pass_rate']:.1%} | {stats['avg_latency_ms']:.1f} | "
            f"{diversity_label} | {stats['errors']} | {notes} |"
        )

    check_summary = summarize_check_metrics(runs)
    if check_summary:
        lines.extend([
            "",
            "## Quality Axis Summary",
            "",
            "| Check | Runs | Pass Rate | Avg Score |",
            "| --- | ---: | ---: | ---: |",
        ])
        for row in check_summary:
            lines.append(
                f"| {row['check_name']} | {row['count']} | "
                f"{row['pass_rate']:.1%} | {row['avg_score']:.3f} |"
            )

    diversity_rows = [
        (baseline, stats)
        for baseline, stats in sorted(comparison_report.items())
        if stats.get("diversity_sample_count", 0) > 0
    ]
    if diversity_rows:
        lines.extend([
            "",
            "## Diversity Summary",
            "",
            "| Baseline | Categories Sampled | Diversity Pass Rate | Avg Diversity Score |",
            "| --- | ---: | ---: | ---: |",
        ])
        for baseline, stats in diversity_rows:
            lines.append(
                f"| {baseline} | {stats.get('diversity_sample_count', 0)} | "
                f"{stats.get('diversity_pass_rate', 0.0):.1%} | "
                f"{stats.get('avg_diversity_score', 0.0):.3f} |"
            )

    lines.extend([
        "",
        "## Category Summary",
        "",
        "| Category | Runs | Errors | Avg Score | Structural |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for category_row in execution_summary["category_summary"]:
        lines.append(
            f"| {category_row['category']} | {category_row['runs']} | "
            f"{category_row['errors']} | {category_row['avg_score']:.3f} | "
            f"{category_row['avg_structural_score']:.3f} |"
        )

    lines.extend([
        "",
        "## Highlights",
        "",
        f"- Best baseline: {best_baseline[0]} ({best_baseline[1]['avg_heuristic_score']:.3f})" if best_baseline else "- Best baseline: n/a",
        f"- Fastest baseline: {fastest_baseline[0]} ({fastest_baseline[1]['avg_latency_ms']:.1f} ms)" if fastest_baseline else "- Fastest baseline: n/a",
        f"- Failing runs: {len(failing_runs)} / {len(runs)}",
        f"- Contract nodes tracked: {contract_doc.get('node_count', 0)}",
        f"- Trace files emitted: {len(trace_paths)}",
        "",
        "## Lowest Scoring Runs",
        "",
        "| Scenario | Category | Baseline | Score | Failed Checks |",
        "| --- | --- | --- | ---: | --- |",
    ])

    for run in bottom_runs:
        lines.append(
            f"| {run.get('scenario_id', 'unknown')} | {run.get('category', 'unknown')} | "
            f"{run.get('baseline', 'unknown')} | "
            f"{run.get('heuristic', {}).get('overall_score', 0.0):.3f} | "
            f"{', '.join(_collect_failed_checks(run)) or '-'} |"
        )

    lines.extend([
        "",
        "## Highest Scoring Runs",
        "",
        "| Scenario | Category | Baseline | Score | Response |",
        "| --- | --- | --- | ---: | --- |",
    ])
    for run in top_runs:
        response_text = str(run.get("response_text") or "").replace("\n", " ").strip()
        lines.append(
            f"| {run.get('scenario_id', 'unknown')} | {run.get('category', 'unknown')} | "
            f"{run.get('baseline', 'unknown')} | "
            f"{run.get('heuristic', {}).get('overall_score', 0.0):.3f} | "
            f"{response_text[:80]}{'...' if len(response_text) > 80 else ''} |"
        )

    if failing_runs:
        lines.extend([
            "",
            "## Failures",
            "",
            "| Scenario | Category | Baseline | Error | Failed Checks |",
            "| --- | --- | --- | --- | --- |",
        ])
        for run in failing_runs[:20]:
            lines.append(
                f"| {run.get('scenario_id', 'unknown')} | {run.get('category', 'unknown')} | "
                f"{run.get('baseline', 'unknown')} | "
                f"{(run.get('error', '-') or '-').replace('|', '/')} | "
                f"{', '.join(_collect_failed_checks(run)) or '-'} |"
            )

    lines.extend([
        "",
        "## Observability",
        "",
        "- `observability/contracts.json`: node contract snapshot",
        "- `observability/architecture.mmd`: mermaid flow generated from reads/writes",
        "- `observability/traces/`: per-run trace JSON",
        "",
    ])

    return "\n".join(lines)


def generate_report_bundle(
    *,
    input_path: Path | None = None,
    category: str | None = None,
    baseline: str = "all",
    persona: str = "cold_attached_idol",
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Generate report artifacts from an existing results file or a fresh run."""
    output_dir = output_dir or REPORTS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path is not None:
        with open(input_path) as f:
            raw = json.load(f)
        results_by_category = normalize_results_blob(raw)
        source_label = f"input:{input_path}"
    else:
        baselines = None if baseline == "all" else [baseline]
        if category:
            raw_results = asyncio.run(run_category(category, baselines, persona))
        else:
            raw_results = asyncio.run(run_all(baselines, persona))
        results_by_category = normalize_results_blob(raw_results)
        source_label = "fresh-run"

    runs = flatten_runs(results_by_category)
    comparison_report = generate_comparison_report(results_by_category)
    execution_summary = summarize_execution(results_by_category)

    observability_dir = output_dir / "observability"
    traces_dir = observability_dir / "traces"
    trace_paths = _save_run_traces(runs, traces_dir)
    contract_doc = generate_contract_docs(observability_dir)

    results_payload = {
        "results": results_by_category,
        "report": comparison_report,
    }
    summary_payload = {
        "execution_summary": execution_summary,
        "comparison_report": comparison_report,
        "trace_count": len(trace_paths),
        "contract_node_count": contract_doc.get("node_count", 0),
    }

    report_md = build_markdown_report(
        results_by_category=results_by_category,
        comparison_report=comparison_report,
        execution_summary=execution_summary,
        trace_paths=trace_paths,
        contract_doc=contract_doc,
        source_label=source_label,
    )

    results_path = output_dir / "results.json"
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "report.md"

    results_path.write_text(json.dumps(results_payload, ensure_ascii=False, indent=2))
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2))
    report_path.write_text(report_md)

    return {
        "report": report_path,
        "results": results_path,
        "summary": summary_path,
        "observability_dir": observability_dir,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate evaluation report bundle")
    parser.add_argument("--input", help="Existing results JSON path")
    parser.add_argument("--category", help="Run a specific category")
    parser.add_argument("--baseline", default="all", help="Baseline name or 'all'")
    parser.add_argument("--persona", default="cold_attached_idol")
    parser.add_argument("--output-dir", help="Output directory for the report bundle")
    args = parser.parse_args()

    configure_logging()
    artifact_paths = generate_report_bundle(
        input_path=Path(args.input) if args.input else None,
        category=args.category,
        baseline=args.baseline,
        persona=args.persona,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )

    print(f"Report: {artifact_paths['report']}")
    print(f"Results: {artifact_paths['results']}")
    print(f"Summary: {artifact_paths['summary']}")
    print(f"Observability: {artifact_paths['observability_dir']}")


if __name__ == "__main__":
    main()
