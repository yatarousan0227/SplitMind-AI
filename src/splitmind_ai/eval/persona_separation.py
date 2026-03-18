"""Persona separation evaluation across representative scenarios and baselines.

Usage:
    uv run python -m splitmind_ai.eval.persona_separation
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from splitmind_ai.app.settings import PROJECT_ROOT
from splitmind_ai.eval.datasets.scenario_loader import load_all_scenarios
from splitmind_ai.eval.runner import run_single_scenario
from splitmind_ai.personas.loader import load_persona

DEFAULT_PERSONAS = [
    "cold_attached_idol",
    "warm_guarded_companion",
    "angelic_but_deliberate",
    "irresistibly_sweet_center_heroine",
]

DEFAULT_BASELINES = [
    "splitmind_full",
    "single_prompt_dedicated",
]

DEFAULT_SCENARIO_IDS = [
    "affection_04",
    "ambiguity_04",
    "jealousy_02",
    "mild_conflict_02",
    "rejection_04",
    "repair_01",
]

MARKER_GROUPS = {
    "warmth": ("嬉しい", "ありがとう", "大事", "ちゃんと嬉しい", "楽しい", "戻って", "受け取る"),
    "guardedness": ("別に", "まあ", "でも", "ただ", "今すぐ", "追わない", "引き止め", "軽く"),
    "status": ("ちゃんと", "そのまま", "次は", "なら", "してて", "決め", "戻ってくるなら"),
    "teasing": ("へえ", "ふーん", "まあ", "そんなに", "ずいぶん"),
    "vulnerability": ("やっぱり", "ちょっと", "少し", "気になる", "嬉しい", "寂しい"),
    "boundary": ("今すぐ", "追わない", "引き止め", "しない", "ただ", "でも"),
}


@dataclass
class PairwiseDistance:
    left: str
    right: str
    text_distance: float
    signature_distance: float
    combined_distance: float


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_selected_scenarios(selected_ids: list[str]) -> list[dict[str, Any]]:
    all_data = load_all_scenarios()
    index: dict[str, dict[str, Any]] = {}
    for dataset in all_data.values():
        for scenario in dataset.get("scenarios", []):
            index[str(scenario.get("id"))] = scenario

    missing = [scenario_id for scenario_id in selected_ids if scenario_id not in index]
    if missing:
        raise FileNotFoundError(f"Scenario ids not found: {missing}")
    return [index[scenario_id] for scenario_id in selected_ids]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[\w一-龠ぁ-んァ-ン]+", text.lower()))


def _jaccard_distance(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens and not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return 1.0 - (len(left_tokens & right_tokens) / len(union))


def _marker_counts(text: str) -> dict[str, float]:
    lowered = text.strip()
    counts: dict[str, float] = {}
    for group, markers in MARKER_GROUPS.items():
        hits = sum(lowered.count(marker) for marker in markers)
        counts[group] = float(hits)
    counts["char_length"] = float(len(lowered))
    counts["sentence_count"] = float(max(1, len(re.findall(r"[。.!?？！]", lowered)))) if lowered else 0.0
    counts["question_count"] = float(lowered.count("?") + lowered.count("？"))
    counts["ellipsis_count"] = float(lowered.count("…") + lowered.count("..."))
    return counts


def _normalized_signature(text: str) -> dict[str, float]:
    counts = _marker_counts(text)
    char_scale = max(1.0, counts["char_length"])
    return {
        "warmth": min(1.0, counts["warmth"] / 2.0),
        "guardedness": min(1.0, counts["guardedness"] / 2.0),
        "status": min(1.0, counts["status"] / 2.0),
        "teasing": min(1.0, counts["teasing"] / 2.0),
        "vulnerability": min(1.0, counts["vulnerability"] / 2.0),
        "boundary": min(1.0, counts["boundary"] / 2.0),
        "question_ratio": min(1.0, counts["question_count"]),
        "ellipsis_ratio": min(1.0, counts["ellipsis_count"]),
        "brevity": max(0.0, min(1.0, 1.0 - (char_scale / 120.0))),
    }


def _signature_distance(left: str, right: str) -> float:
    left_sig = _normalized_signature(left)
    right_sig = _normalized_signature(right)
    keys = sorted(left_sig)
    squared = [(left_sig[key] - right_sig[key]) ** 2 for key in keys]
    return math.sqrt(sum(squared) / len(squared))


def _config_axes(persona_name: str) -> dict[str, float]:
    raw = load_persona(persona_name).raw
    psych = raw.get("psychodynamics", {}) or {}
    rel = raw.get("relational_profile", {}) or {}
    ego = raw.get("ego_organization", {}) or {}
    safety = raw.get("safety_boundary", {}) or {}

    drives = psych.get("drives", {}) or {}
    threats = psych.get("threat_sensitivity", {}) or {}
    superego = psych.get("superego_configuration", {}) or {}
    intimacy = rel.get("intimacy_regulation", {}) or {}
    trust = rel.get("trust_dynamics", {}) or {}
    dependency = rel.get("dependency_model", {}) or {}
    exclusivity = rel.get("exclusivity_orientation", {}) or {}
    repair = rel.get("repair_orientation", {}) or {}
    hard_limits = safety.get("hard_limits", {}) or {}

    warmth_drive = max(
        _safe_float(drives.get("closeness")),
        _safe_float(drives.get("approval")),
        _safe_float(drives.get("care")),
    )

    return {
        "warmth_readiness": (
            warmth_drive
            + _safe_float(ego.get("warmth_recovery_speed"))
            + _safe_float(ego.get("self_disclosure_tolerance"))
            + _safe_float(hard_limits.get("max_direct_neediness"))
        ) / 4.0,
        "guardedness": (
            _safe_float(intimacy.get("preferred_distance"))
            + (1.0 - _safe_float(intimacy.get("closeness_acceleration_tolerance"), 0.5))
            + _safe_float(superego.get("dependency_shame"))
            + _safe_float(superego.get("emotional_exposure_taboo"))
            + (1.0 - _safe_float(hard_limits.get("max_self_exposure_when_unfamiliar"), 0.5))
        ) / 5.0,
        "status_maintenance": (
            _safe_float(drives.get("status"))
            + _safe_float(superego.get("pride_rigidity"))
            + _safe_float(repair.get("status_preservation_need"))
        ) / 3.0,
        "repair_openness": (
            _safe_float(repair.get("apology_receptivity"))
            + _safe_float(trust.get("repair_recovery_speed"))
            + (1.0 - _safe_float(repair.get("forgiveness_latency"), 0.5))
            + _safe_float(ego.get("warmth_recovery_speed"))
        ) / 4.0,
        "jealousy_reactivity": (
            _safe_float(exclusivity.get("desires_priority"))
            + _safe_float(exclusivity.get("jealousy_reactivity"))
            + _safe_float(threats.get("undervaluation"))
            + _safe_float(threats.get("rejection"))
        ) / 4.0,
        "self_disclosure_capacity": (
            _safe_float(dependency.get("displays_own_dependence"))
            + _safe_float(ego.get("self_disclosure_tolerance"))
            + _safe_float(hard_limits.get("max_self_exposure_when_unfamiliar"))
        ) / 3.0,
    }


def _pairwise_distances(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for idx, left in enumerate(runs):
        for right in runs[idx + 1 :]:
            text_distance = _jaccard_distance(left["response_text"], right["response_text"])
            signature_distance = _signature_distance(left["response_text"], right["response_text"])
            combined = text_distance * 0.65 + signature_distance * 0.35
            results.append(asdict(PairwiseDistance(
                left=left["persona"],
                right=right["persona"],
                text_distance=round(text_distance, 4),
                signature_distance=round(signature_distance, 4),
                combined_distance=round(combined, 4),
            )))
    return results


def _aggregate_baseline_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_baseline: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_baseline.setdefault(run["baseline"], []).append(run)

    summary: dict[str, Any] = {}
    for baseline, baseline_runs in sorted(by_baseline.items()):
        scenario_pairwise: list[float] = []
        persona_scores: dict[str, list[float]] = {}
        for run in baseline_runs:
            persona_scores.setdefault(run["persona"], []).append(run["heuristic"]["overall_score"])

        grouped: dict[str, list[dict[str, Any]]] = {}
        for run in baseline_runs:
            grouped.setdefault(run["scenario_id"], []).append(run)

        collapse_pairs = 0
        pair_count = 0
        for scenario_runs in grouped.values():
            for pair in _pairwise_distances(scenario_runs):
                scenario_pairwise.append(pair["combined_distance"])
                pair_count += 1
                if pair["combined_distance"] < 0.32:
                    collapse_pairs += 1

        summary[baseline] = {
            "avg_pairwise_distance": round(sum(scenario_pairwise) / len(scenario_pairwise), 4) if scenario_pairwise else 0.0,
            "min_pairwise_distance": round(min(scenario_pairwise), 4) if scenario_pairwise else 0.0,
            "collapse_pair_rate": round(collapse_pairs / pair_count, 4) if pair_count else 0.0,
            "avg_heuristic_score": round(
                sum(run["heuristic"]["overall_score"] for run in baseline_runs) / len(baseline_runs),
                4,
            ) if baseline_runs else 0.0,
            "avg_structural_score": round(
                sum(run["heuristic"]["structural_score"] for run in baseline_runs) / len(baseline_runs),
                4,
            ) if baseline_runs else 0.0,
            "persona_avg_scores": {
                persona: round(sum(scores) / len(scores), 4)
                for persona, scores in sorted(persona_scores.items())
            },
        }
    return summary


def _aggregate_persona_behavior(runs: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for run in runs:
        grouped.setdefault((run["baseline"], run["persona"]), []).append(run)

    summary: dict[str, Any] = {}
    for (baseline, persona), persona_runs in sorted(grouped.items()):
        signatures = [_normalized_signature(run["response_text"]) for run in persona_runs]
        aggregated = {
            key: round(sum(sig[key] for sig in signatures) / len(signatures), 4)
            for key in sorted(signatures[0])
        } if signatures else {}
        summary.setdefault(baseline, {})[persona] = {
            "avg_signature": aggregated,
            "avg_heuristic_score": round(
                sum(run["heuristic"]["overall_score"] for run in persona_runs) / len(persona_runs),
                4,
            ) if persona_runs else 0.0,
            "avg_structural_score": round(
                sum(run["heuristic"]["structural_score"] for run in persona_runs) / len(persona_runs),
                4,
            ) if persona_runs else 0.0,
        }
    return summary


def _build_markdown_report(
    *,
    scenarios: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    personas: list[str],
    baselines: list[str],
    scenario_ids: list[str],
    config_axes: dict[str, dict[str, float]],
    baseline_summary: dict[str, Any],
    persona_behavior: dict[str, Any],
) -> str:
    scenario_lookup = {scenario["id"]: scenario for scenario in scenarios}
    lines = [
        "# Persona Separation Evaluation",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Personas: {', '.join(personas)}",
        f"- Baselines: {', '.join(baselines)}",
        f"- Scenarios: {', '.join(s['id'] for s in scenarios)}",
        "",
        "## Baseline Summary",
        "",
        "| Baseline | Avg Pairwise Distance | Min Pairwise Distance | Collapse Pair Rate | Avg Heuristic | Avg Structural |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for baseline, stats in baseline_summary.items():
        lines.append(
            f"| {baseline} | {stats['avg_pairwise_distance']:.3f} | {stats['min_pairwise_distance']:.3f} | "
            f"{stats['collapse_pair_rate']:.1%} | {stats['avg_heuristic_score']:.3f} | "
            f"{stats['avg_structural_score']:.3f} |"
        )

    lines.extend([
        "",
        "## Persona Config Axes",
        "",
        "| Persona | Warmth | Guardedness | Status | Repair Openness | Jealousy | Disclosure |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for persona, axes in config_axes.items():
        lines.append(
            f"| {persona} | {axes['warmth_readiness']:.3f} | {axes['guardedness']:.3f} | "
            f"{axes['status_maintenance']:.3f} | {axes['repair_openness']:.3f} | "
            f"{axes['jealousy_reactivity']:.3f} | {axes['self_disclosure_capacity']:.3f} |"
        )

    for baseline in baselines:
        lines.extend([
            "",
            f"## {baseline} Persona Signatures",
            "",
            "| Persona | Warmth | Guarded | Status | Teasing | Vulnerability | Boundary | Brevity | Avg Score |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for persona, info in persona_behavior.get(baseline, {}).items():
            signature = info["avg_signature"]
            lines.append(
                f"| {persona} | {signature.get('warmth', 0.0):.3f} | {signature.get('guardedness', 0.0):.3f} | "
                f"{signature.get('status', 0.0):.3f} | {signature.get('teasing', 0.0):.3f} | "
                f"{signature.get('vulnerability', 0.0):.3f} | {signature.get('boundary', 0.0):.3f} | "
                f"{signature.get('brevity', 0.0):.3f} | {info['avg_heuristic_score']:.3f} |"
            )

    for scenario_id in scenario_ids:
        scenario_runs = [run for run in runs if run["scenario_id"] == scenario_id]
        if not scenario_runs:
            continue
        scenario = scenario_lookup[scenario_id]
        lines.extend([
            "",
            f"## Scenario {scenario_id}",
            "",
            f"- Category: {scenario.get('category', '')}",
            f"- User message: {scenario.get('user_message', '')}",
            "",
            "| Baseline | Persona | Response | Appraisal | Residue | Score | Structural |",
            "| --- | --- | --- | --- | --- | ---: | ---: |",
        ])
        for run in sorted(scenario_runs, key=lambda item: (item["baseline"], item["persona"])):
            appraisal = (run.get("appraisal") or {}).get("event_type", "-")
            residue = ((run.get("conflict_state") or {}).get("residue") or {}).get("visible_emotion", "-")
            response = run["response_text"].replace("\n", " ").strip()
            lines.append(
                f"| {run['baseline']} | {run['persona']} | {response[:80]}{'...' if len(response) > 80 else ''} | "
                f"{appraisal} | {residue} | {run['heuristic']['overall_score']:.3f} | "
                f"{run['heuristic']['structural_score']:.3f} |"
            )

    return "\n".join(lines) + "\n"


async def run_persona_separation_eval(
    *,
    personas: list[str],
    baselines: list[str],
    scenario_ids: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = _load_selected_scenarios(scenario_ids)
    config_axes = {persona: _config_axes(persona) for persona in personas}

    runs: list[dict[str, Any]] = []
    for scenario in scenarios:
        for baseline in baselines:
            for persona in personas:
                result = await run_single_scenario(scenario, baseline, persona)
                run = {
                    "scenario_id": result["scenario_id"],
                    "category": result.get("category", scenario.get("category", "")),
                    "baseline": baseline,
                    "persona": persona,
                    "response_text": result.get("response_text", ""),
                    "heuristic": result.get("heuristic", {}),
                    "appraisal": result.get("appraisal"),
                    "conflict_state": result.get("conflict_state"),
                    "relationship_state": result.get("relationship_state"),
                    "fidelity_gate": result.get("fidelity_gate"),
                    "latency_ms": result.get("latency_ms"),
                    "payload": result.get("payload"),
                    "response_signature": _normalized_signature(result.get("response_text", "")),
                }
                runs.append(run)
                (output_dir / "runs.partial.json").write_text(json.dumps(runs, ensure_ascii=False, indent=2) + "\n")

    scenario_pairwise: dict[str, dict[str, Any]] = {}
    for baseline in baselines:
        baseline_runs = [run for run in runs if run["baseline"] == baseline]
        for scenario_id in scenario_ids:
            scenario_runs = [run for run in baseline_runs if run["scenario_id"] == scenario_id]
            scenario_pairwise.setdefault(baseline, {})[scenario_id] = _pairwise_distances(scenario_runs)

    baseline_summary = _aggregate_baseline_summary(runs)
    persona_behavior = _aggregate_persona_behavior(runs)
    report_md = _build_markdown_report(
        scenarios=scenarios,
        runs=runs,
        personas=personas,
        baselines=baselines,
        scenario_ids=scenario_ids,
        config_axes=config_axes,
        baseline_summary=baseline_summary,
        persona_behavior=persona_behavior,
    )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "personas": personas,
        "baselines": baselines,
        "scenario_ids": scenario_ids,
        "config_axes": config_axes,
        "baseline_summary": baseline_summary,
        "persona_behavior": persona_behavior,
        "scenario_pairwise": scenario_pairwise,
        "runs": runs,
    }
    return {
        "payload": payload,
        "report_md": report_md,
    }


def _default_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return PROJECT_ROOT / "output" / "persona_separation" / stamp


def main() -> None:
    parser = argparse.ArgumentParser(description="Persona separation evaluation")
    parser.add_argument("--output-dir", help="Directory to write evaluation artifacts")
    parser.add_argument("--personas", nargs="*", default=DEFAULT_PERSONAS)
    parser.add_argument("--baselines", nargs="*", default=DEFAULT_BASELINES)
    parser.add_argument("--scenario-ids", nargs="*", default=DEFAULT_SCENARIO_IDS)
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir()
    result = asyncio.run(
        run_persona_separation_eval(
            personas=list(args.personas),
            baselines=list(args.baselines),
            scenario_ids=list(args.scenario_ids),
            output_dir=output_dir,
        )
    )

    payload = result["payload"]
    (output_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "baseline_summary": payload["baseline_summary"],
                "config_axes": payload["config_axes"],
                "scenario_ids": payload["scenario_ids"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    )
    (output_dir / "report.md").write_text(result["report_md"])

    print(f"Results: {output_dir / 'results.json'}")
    print(f"Summary: {output_dir / 'summary.json'}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
