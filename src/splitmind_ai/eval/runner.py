"""Evaluation runner: execute scenarios across baselines and collect results.

Usage:
    python -m splitmind_ai.eval.runner [--category jealousy] [--baseline all]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from splitmind_ai.app.logging_utils import configure_logging, preview_text
from splitmind_ai.eval.baselines import BASELINES, BaselineConfig, build_baseline_graph
from splitmind_ai.eval.datasets.scenario_loader import load_all_scenarios, load_scenario
from splitmind_ai.eval.heuristic import (
    HeuristicResult,
    evaluate_response_set_diversity,
    evaluate_scenario_run,
)
from splitmind_ai.personas.loader import load_persona

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


# ---------------------------------------------------------------------------
# Single scenario run
# ---------------------------------------------------------------------------

async def run_single_scenario(
    scenario: dict[str, Any],
    baseline_name: str,
    persona_name: str = "cold_attached_idol",
) -> dict[str, Any]:
    """Execute a single scenario against a single baseline.

    Returns a dict with: scenario_id, baseline, response_text, dynamics,
    supervisor, heuristic_result, latency_ms, token_usage.
    """
    baseline_cfg = BASELINES.get(baseline_name)
    if baseline_cfg is None:
        raise ValueError(f"Unknown baseline: {baseline_name}")

    persona = load_persona(persona_name)

    # Build initial state from scenario
    state: dict[str, Any] = {
        "request": {
            "session_id": f"eval-{scenario.get('id', 'unknown')}",
            "user_id": "eval_user",
            "user_message": scenario["user_message"],
            "message": scenario["user_message"],
            "action": "chat",
        },
        "response": {},
        "relationship": scenario.get("prior_relationship", {}),
        "mood": scenario.get("prior_mood", {}),
        "_internal": {
            "is_first_turn": True,
            "turn_count": 0,
        },
    }

    logger.debug(
        "eval run start scenario=%s baseline=%s persona=%s message=%s",
        scenario.get("id", "unknown"),
        baseline_name,
        persona_name,
        preview_text(scenario["user_message"]),
    )
    # Build and run graph
    compiled = build_baseline_graph(baseline_cfg, persona_name=persona_name)
    start = time.monotonic()
    result = await compiled.ainvoke(state)
    latency_ms = (time.monotonic() - start) * 1000
    logger.debug(
        "eval run complete scenario=%s baseline=%s latency_ms=%.1f status=%s response=%s",
        scenario.get("id", "unknown"),
        baseline_name,
        latency_ms,
        result.get("_internal", {}).get("status"),
        preview_text(result.get("response", {}).get("final_response_text")),
    )

    # Extract outputs
    response = result.get("response", {})
    response_text = response.get("final_response_text", "")
    dynamics = result.get("dynamics", {})
    supervisor = response  # supervisor plan is merged into response

    # Run heuristic evaluation
    heuristic = evaluate_scenario_run(
        scenario=scenario,
        response_text=response_text,
        dynamics_output=dynamics,
        supervisor_output=supervisor,
        conversation_policy=result.get("conversation_policy"),
        drive_state=result.get("drive_state"),
        inhibition_state=result.get("inhibition_state"),
        persona_weights=persona.weights,
        persona_leakage_policy=persona.leakage_policy,
        banned_expressions=persona.prohibited_expressions,
        updated_relationship=result.get("relationship"),
        updated_mood=result.get("mood"),
    )

    return {
        "scenario_id": scenario.get("id", "unknown"),
        "category": scenario.get("category", ""),
        "baseline": baseline_name,
        "response_text": response_text,
        "dynamics": dynamics,
        "drive_state": result.get("drive_state", {}),
        "inhibition_state": result.get("inhibition_state", {}),
        "heuristic": heuristic.to_dict(),
        "latency_ms": round(latency_ms, 1),
    }


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_category(
    category: str,
    baseline_names: list[str] | None = None,
    persona_name: str = "cold_attached_idol",
) -> list[dict[str, Any]]:
    """Run all scenarios in a category across specified baselines."""
    data = load_scenario(category)
    scenarios = data.get("scenarios", [])
    baselines = baseline_names or list(BASELINES.keys())
    results: list[dict[str, Any]] = []

    for scenario in scenarios:
        # Inject category from parent
        scenario["category"] = data.get("category", category)
        for bl in baselines:
            try:
                result = await run_single_scenario(scenario, bl, persona_name)
                results.append(result)
                logger.info(
                    "OK scenario=%s baseline=%s score=%.2f",
                    scenario.get("id"),
                    bl,
                    result["heuristic"]["overall_score"],
                )
            except Exception as e:
                logger.error(
                    "FAIL scenario=%s baseline=%s error=%s",
                    scenario.get("id"), bl, e,
                )
                results.append({
                    "scenario_id": scenario.get("id", "unknown"),
                    "category": data.get("category", category),
                    "baseline": bl,
                    "error": str(e),
                })

    return results


async def run_all(
    baseline_names: list[str] | None = None,
    persona_name: str = "cold_attached_idol",
) -> dict[str, list[dict[str, Any]]]:
    """Run all categories across all baselines."""
    all_data = load_all_scenarios()
    all_results: dict[str, list[dict[str, Any]]] = {}

    for category_name, data in all_data.items():
        scenarios = data.get("scenarios", [])
        baselines = baseline_names or list(BASELINES.keys())
        results: list[dict[str, Any]] = []

        for scenario in scenarios:
            scenario["category"] = data.get("category", category_name)
            for bl in baselines:
                try:
                    result = await run_single_scenario(scenario, bl, persona_name)
                    results.append(result)
                except Exception as e:
                    results.append({
                        "scenario_id": scenario.get("id", "unknown"),
                        "category": data.get("category", category_name),
                        "baseline": bl,
                        "error": str(e),
                    })

        all_results[category_name] = results

    return all_results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_comparison_report(
    results: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Generate a comparison report across baselines.

    Returns summary with per-baseline metrics:
    - avg_heuristic_score
    - avg_latency_ms
    - contradiction_rate
    - pass_rate
    """
    baseline_stats: dict[str, dict[str, Any]] = {}

    for _category, runs in results.items():
        for run in runs:
            bl = run.get("baseline", "unknown")
            if bl not in baseline_stats:
                baseline_stats[bl] = {
                    "total": 0,
                    "passed": 0,
                    "score_sum": 0.0,
                    "latency_sum": 0.0,
                    "errors": 0,
                    "check_stats": {},
                }
            stats = baseline_stats[bl]
            stats["total"] += 1

            if "error" in run:
                stats["errors"] += 1
                continue

            heuristic = run.get("heuristic", {})
            stats["score_sum"] += heuristic.get("overall_score", 0.0)
            stats["latency_sum"] += run.get("latency_ms", 0.0)
            if heuristic.get("all_passed", False):
                stats["passed"] += 1

            for check in heuristic.get("checks", []):
                check_name = check.get("check_name", "unknown")
                check_stats = stats["check_stats"].setdefault(check_name, {
                    "total": 0,
                    "passed": 0,
                    "score_sum": 0.0,
                })
                check_stats["total"] += 1
                check_stats["passed"] += 1 if check.get("passed", False) else 0
                check_stats["score_sum"] += float(check.get("score", 0.0))

    diversity_by_baseline: dict[str, list[dict[str, Any]]] = {}
    for category, runs in results.items():
        responses_by_baseline: dict[str, list[str]] = {}
        for run in runs:
            if "error" in run:
                continue
            baseline = run.get("baseline", "unknown")
            response_text = (run.get("response_text", "") or "").strip()
            if not response_text:
                continue
            responses_by_baseline.setdefault(baseline, []).append(response_text)

        for baseline, responses in responses_by_baseline.items():
            if len(responses) < 2:
                continue
            diversity_score = evaluate_response_set_diversity(responses)
            diversity_by_baseline.setdefault(baseline, []).append({
                "category": category,
                "score": diversity_score.score,
                "passed": diversity_score.passed,
                "detail": diversity_score.detail,
            })

    report: dict[str, Any] = {}
    for bl, stats in baseline_stats.items():
        valid = stats["total"] - stats["errors"]
        diversity_rows = diversity_by_baseline.get(bl, [])
        diversity_sample_count = len(diversity_rows)
        avg_diversity_score = (
            sum(row["score"] for row in diversity_rows) / diversity_sample_count
            if diversity_sample_count > 0 else None
        )
        diversity_pass_rate = (
            sum(1 for row in diversity_rows if row["passed"]) / diversity_sample_count
            if diversity_sample_count > 0 else None
        )

        check_pass_rates: dict[str, dict[str, float]] = {}
        for check_name, check_stats in sorted(stats["check_stats"].items()):
            total = check_stats["total"]
            check_pass_rates[check_name] = {
                "pass_rate": check_stats["passed"] / total if total > 0 else 0.0,
                "avg_score": check_stats["score_sum"] / total if total > 0 else 0.0,
            }

        report[bl] = {
            "total_scenarios": stats["total"],
            "errors": stats["errors"],
            "avg_heuristic_score": stats["score_sum"] / valid if valid > 0 else 0.0,
            "avg_latency_ms": stats["latency_sum"] / valid if valid > 0 else 0.0,
            "pass_rate": stats["passed"] / valid if valid > 0 else 0.0,
            "contradiction_rate": 1.0 - (stats["passed"] / valid if valid > 0 else 0.0),
            "avg_diversity_score": avg_diversity_score,
            "diversity_pass_rate": diversity_pass_rate,
            "diversity_sample_count": diversity_sample_count,
            "check_pass_rates": check_pass_rates,
        }

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _save_results(data: Any, name: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="SplitMind-AI evaluation runner")
    parser.add_argument("--category", help="Run a specific category (e.g. jealousy)")
    parser.add_argument("--baseline", default="all", help="Baseline name or 'all'")
    parser.add_argument("--persona", default="cold_attached_idol")
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()

    configure_logging()

    baselines = None if args.baseline == "all" else [args.baseline]

    if args.category:
        results = asyncio.run(run_category(args.category, baselines, args.persona))
        out = _save_results(results, f"eval_{args.category}")
    else:
        all_results = asyncio.run(run_all(baselines, args.persona))
        report = generate_comparison_report(all_results)
        combined = {"results": all_results, "report": report}
        out = _save_results(combined, "eval_full")

    print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
