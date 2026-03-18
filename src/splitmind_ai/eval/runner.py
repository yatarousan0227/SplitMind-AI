"""Evaluation runner: execute scenarios across baselines and collect results.

Usage:
    uv run python -m splitmind_ai.eval.runner [--category jealousy] [--baseline all]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from splitmind_ai.app.language import detect_response_language
from splitmind_ai.app.logging_utils import configure_logging, preview_text
from splitmind_ai.eval.baselines import BASELINES, build_baseline_graph
from splitmind_ai.eval.datasets.scenario_loader import load_all_scenarios, load_scenario
from splitmind_ai.eval.heuristic import evaluate_response_set_diversity, evaluate_scenario_run
from splitmind_ai.eval.single_prompt_chat import run_single_prompt_chat
from splitmind_ai.personas.loader import load_persona

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


async def run_single_scenario(
    scenario: dict[str, Any],
    baseline_name: str,
    persona_name: str = "cold_attached_idol",
) -> dict[str, Any]:
    """Execute a single scenario against one baseline."""
    baseline_cfg = BASELINES.get(baseline_name)
    if baseline_cfg is None:
        raise ValueError(f"Unknown baseline: {baseline_name}")

    persona = load_persona(persona_name)
    logger.debug(
        "eval run start scenario=%s baseline=%s persona=%s message=%s",
        scenario.get("id", "unknown"),
        baseline_name,
        persona_name,
        preview_text(str(scenario.get("user_message") or "")),
    )

    start = time.monotonic()
    if baseline_cfg.kind == "graph":
        compiled = build_baseline_graph(baseline_cfg, persona_name=persona_name)
        result = await compiled.ainvoke(_build_seed_state(scenario, persona_name, persona.to_slice()))
        response = result.get("response", {}) or {}
        response_text = str(response.get("final_response_text") or "")
        appraisal = result.get("appraisal") or None
        conflict_state = result.get("conflict_state") or None
        relationship_state = result.get("relationship_state") or None
        trace = result.get("trace", {}) or {}
        fidelity_gate = trace.get("fidelity_gate") or None
        payload: dict[str, Any] = {
            "response": response,
            "appraisal": appraisal,
            "conflict_state": conflict_state,
            "relationship_state": relationship_state,
            "trace": trace,
        }
        status = result.get("_internal", {}).get("status")
    elif baseline_cfg.kind == "single_prompt":
        result = run_single_prompt_chat(
            persona_name=persona_name,
            messages=[str(scenario.get("user_message") or "")],
            persona_format=baseline_cfg.persona_format or "raw",
            include_summary_memo=baseline_cfg.include_summary_memo,
        )
        turns = list(result.get("turns", []) or [])
        response_text = str((turns[-1] if turns else {}).get("assistant") or "")
        appraisal = None
        conflict_state = None
        relationship_state = None
        fidelity_gate = None
        payload = {
            "system_prompt": result.get("system_prompt", ""),
            "turns": turns,
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
        }
        status = "completed"
    else:
        raise ValueError(f"Unsupported baseline kind: {baseline_cfg.kind}")
    latency_ms = (time.monotonic() - start) * 1000

    heuristic = evaluate_scenario_run(
        scenario=scenario,
        response_text=response_text,
        appraisal=appraisal,
        conflict_state=conflict_state,
        relationship_state=relationship_state,
        fidelity_gate=fidelity_gate,
    )

    logger.debug(
        "eval run complete scenario=%s baseline=%s latency_ms=%.1f status=%s response=%s score=%.2f structural=%.2f",
        scenario.get("id", "unknown"),
        baseline_name,
        latency_ms,
        status,
        preview_text(response_text),
        heuristic.overall_score,
        heuristic.structural_score,
    )

    return {
        "scenario_id": scenario.get("id", "unknown"),
        "category": scenario.get("category", ""),
        "baseline": baseline_name,
        "baseline_kind": baseline_cfg.kind,
        "response_text": response_text,
        "appraisal": appraisal,
        "conflict_state": conflict_state,
        "relationship_state": relationship_state,
        "fidelity_gate": fidelity_gate,
        "payload": payload,
        "heuristic": heuristic.to_dict(),
        "latency_ms": round(latency_ms, 1),
    }


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
        scenario["category"] = data.get("category", category)
        for baseline_name in baselines:
            try:
                result = await run_single_scenario(scenario, baseline_name, persona_name)
                results.append(result)
                logger.info(
                    "OK scenario=%s baseline=%s score=%.2f structural=%.2f",
                    scenario.get("id"),
                    baseline_name,
                    result["heuristic"]["overall_score"],
                    result["heuristic"]["structural_score"],
                )
            except Exception as exc:
                logger.error(
                    "FAIL scenario=%s baseline=%s error=%s",
                    scenario.get("id"),
                    baseline_name,
                    exc,
                )
                results.append({
                    "scenario_id": scenario.get("id", "unknown"),
                    "category": data.get("category", category),
                    "baseline": baseline_name,
                    "error": str(exc),
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
            for baseline_name in baselines:
                try:
                    result = await run_single_scenario(scenario, baseline_name, persona_name)
                    results.append(result)
                except Exception as exc:
                    results.append({
                        "scenario_id": scenario.get("id", "unknown"),
                        "category": data.get("category", category_name),
                        "baseline": baseline_name,
                        "error": str(exc),
                    })

        all_results[category_name] = results

    return all_results


def generate_comparison_report(
    results: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Generate a baseline comparison report from runner output."""
    baseline_stats: dict[str, dict[str, Any]] = {}

    for runs in results.values():
        for run in runs:
            baseline_name = run.get("baseline", "unknown")
            stats = baseline_stats.setdefault(
                baseline_name,
                {
                    "total": 0,
                    "passed": 0,
                    "score_sum": 0.0,
                    "structural_sum": 0.0,
                    "latency_sum": 0.0,
                    "errors": 0,
                    "check_stats": {},
                },
            )
            stats["total"] += 1

            if "error" in run:
                stats["errors"] += 1
                continue

            heuristic = run.get("heuristic", {}) or {}
            stats["score_sum"] += float(heuristic.get("overall_score", 0.0))
            stats["structural_sum"] += float(heuristic.get("structural_score", 0.0))
            stats["latency_sum"] += float(run.get("latency_ms", 0.0))
            if heuristic.get("all_passed", False):
                stats["passed"] += 1

            for check in heuristic.get("checks", []):
                check_name = check.get("check_name", "unknown")
                check_stats = stats["check_stats"].setdefault(
                    check_name,
                    {"total": 0, "passed": 0, "score_sum": 0.0},
                )
                check_stats["total"] += 1
                check_stats["passed"] += 1 if check.get("passed", False) else 0
                check_stats["score_sum"] += float(check.get("score", 0.0))

    diversity_by_baseline: dict[str, list[dict[str, Any]]] = {}
    for category, runs in results.items():
        responses_by_baseline: dict[str, list[str]] = {}
        for run in runs:
            if "error" in run:
                continue
            baseline_name = run.get("baseline", "unknown")
            response_text = str(run.get("response_text") or "").strip()
            if response_text:
                responses_by_baseline.setdefault(baseline_name, []).append(response_text)

        for baseline_name, responses in responses_by_baseline.items():
            if len(responses) < 2:
                continue
            diversity_score = evaluate_response_set_diversity(responses)
            diversity_by_baseline.setdefault(baseline_name, []).append({
                "category": category,
                "score": diversity_score,
                "passed": diversity_score >= 0.55,
            })

    report: dict[str, Any] = {}
    for baseline_name, stats in baseline_stats.items():
        valid = stats["total"] - stats["errors"]
        diversity_rows = diversity_by_baseline.get(baseline_name, [])
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

        pass_rate = stats["passed"] / valid if valid > 0 else 0.0
        report[baseline_name] = {
            "total_scenarios": stats["total"],
            "errors": stats["errors"],
            "avg_heuristic_score": stats["score_sum"] / valid if valid > 0 else 0.0,
            "avg_structural_score": stats["structural_sum"] / valid if valid > 0 else 0.0,
            "avg_latency_ms": stats["latency_sum"] / valid if valid > 0 else 0.0,
            "pass_rate": pass_rate,
            "contradiction_rate": 1.0 - pass_rate,
            "avg_diversity_score": avg_diversity_score,
            "diversity_pass_rate": diversity_pass_rate,
            "diversity_sample_count": diversity_sample_count,
            "check_pass_rates": check_pass_rates,
        }

    return report


def _build_seed_state(
    scenario: dict[str, Any],
    persona_name: str,
    persona_slice: dict[str, Any],
) -> dict[str, Any]:
    user_message = str(scenario.get("user_message") or "")
    session_id = f"eval-{scenario.get('category', 'unknown')}-{scenario.get('id', 'unknown')}"
    prior_state = dict(scenario.get("prior_state", {}) or {})
    relationship_state = dict(prior_state.get("relationship_state", {}) or {})
    mood = dict(prior_state.get("mood", {}) or {})
    return {
        "request": {
            "session_id": session_id,
            "user_id": "eval_user",
            "user_message": user_message,
            "message": user_message,
            "action": "chat",
            "response_language": detect_response_language(user_message, None),
            "turn_number": 1,
        },
        "response": {},
        "conversation": {
            "recent_messages": [],
            "summary": None,
            "turn_count": 0,
        },
        "persona": persona_slice,
        "relationship_state": relationship_state,
        "mood": mood,
        "memory": {
            "session_summaries": [],
            "emotional_memories": [],
            "semantic_preferences": [],
        },
        "working_memory": {
            "active_themes": [],
            "salient_user_phrases": [],
            "retrieved_memory_ids": [],
            "unresolved_questions": [],
            "current_episode_summary": None,
            "recent_conflict_summaries": [],
        },
        "drive_state": {},
        "_internal": {
            "session": {
                "session_id": session_id,
                "persona_name": persona_name,
                "user_id": "eval_user",
            },
            "event_flags": {},
            "errors": [],
            "status": "seeded_for_eval",
            "is_first_turn": False,
            "turn_count": 0,
        },
    }


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
