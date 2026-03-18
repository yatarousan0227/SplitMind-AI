"""Next-generation evaluation heuristics aligned to the conflict-engine runtime."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

_EXPOSITION_MARKERS = (
    "つまり",
    "要するに",
    "大切なのは",
    "気持ち",
    "感情",
    "本音",
    "心理",
    "構造",
)

_COUNSELORISH_MARKERS = (
    "無理しなくていい",
    "あなたのペース",
    "話してくれてありがとう",
    "教えて",
)

_DIRECT_COMMITMENT_MARKERS = (
    "付き合おう",
    "付き合って",
    "愛してる",
    "大好き",
    "ずっと一緒",
)

_ROUGHNESS_HINTS = ("…", "...", "別に", "まあ", "ちょっと", "少し", "ふーん", "へえ")


@dataclass
class HeuristicScore:
    """Score from a single heuristic check."""

    check_name: str
    passed: bool
    score: float
    detail: str = ""
    group: str = "shared"


@dataclass
class HeuristicResult:
    """Aggregate result of heuristic checks for one scenario run."""

    scenario_id: str
    scores: list[HeuristicScore] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        shared = [s.score for s in self.scores if s.group == "shared"]
        if not shared:
            return 0.0
        return sum(shared) / len(shared)

    @property
    def structural_score(self) -> float:
        structural = [s.score for s in self.scores if s.group == "structural"]
        if not structural:
            return 0.0
        return sum(structural) / len(structural)

    @property
    def all_passed(self) -> bool:
        shared = [s for s in self.scores if s.group == "shared"]
        return all(s.passed for s in shared) if shared else True

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "overall_score": self.overall_score,
            "structural_score": self.structural_score,
            "all_passed": self.all_passed,
            "checks": [
                {
                    "check_name": s.check_name,
                    "passed": s.passed,
                    "score": s.score,
                    "detail": s.detail,
                    "group": s.group,
                }
                for s in self.scores
            ],
        }


def evaluate_scenario_run(
    *,
    scenario: dict[str, Any],
    response_text: str,
    appraisal: dict[str, Any] | None = None,
    conflict_state: dict[str, Any] | None = None,
    relationship_state: dict[str, Any] | None = None,
    fidelity_gate: dict[str, Any] | None = None,
) -> HeuristicResult:
    """Evaluate one scenario run against shared and structural checks."""
    result = HeuristicResult(scenario_id=str(scenario.get("id", "unknown")))
    expectations = dict(scenario.get("evaluation_expectations", {}) or {})

    result.scores.extend([
        _check_response_nonempty(response_text),
        _check_forbidden_patterns(response_text, expectations.get("forbidden_response_patterns", [])),
        _check_anti_exposition(response_text),
        _check_counselorish_register(response_text),
        _check_direct_commitment_guard(
            response_text,
            disallow_direct_commitment=bool(expectations.get("disallow_direct_commitment", False)),
        ),
        _check_response_shape(response_text),
    ])

    if appraisal:
        result.scores.append(_check_event_fit(appraisal, expectations.get("event_types_any", [])))
        result.scores.append(_check_perspective_integrity(appraisal, response_text))
    if conflict_state:
        result.scores.append(_check_move_fit(conflict_state, expectations.get("move_families_any", [])))
        result.scores.append(_check_move_style_fit(conflict_state, expectations.get("move_styles_any", [])))
        result.scores.append(_check_conflict_presence(conflict_state))
    if relationship_state:
        result.scores.append(
            _check_relationship_delta(
                prior_state=(scenario.get("prior_state", {}) or {}).get("relationship_state", {}),
                updated_state=relationship_state,
                hints=expectations.get("relationship_delta", {}),
            )
        )
    if fidelity_gate:
        result.scores.append(_check_fidelity_gate(fidelity_gate, appraisal=appraisal or {}))

    return result


def _check_response_nonempty(response_text: str) -> HeuristicScore:
    text = response_text.strip()
    passed = bool(text)
    return HeuristicScore(
        check_name="response_nonempty",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail="response is empty" if not passed else "",
    )


def _check_forbidden_patterns(response_text: str, patterns: list[str]) -> HeuristicScore:
    hits = [pattern for pattern in patterns if pattern and re.search(pattern, response_text)]
    passed = not hits
    return HeuristicScore(
        check_name="forbidden_patterns",
        passed=passed,
        score=0.0 if hits else 1.0,
        detail=", ".join(hits[:3]),
    )

def _check_anti_exposition(response_text: str) -> HeuristicScore:
    text = response_text.strip()
    if not text:
        return HeuristicScore("anti_exposition", False, 0.0, "empty response")

    length_penalty = max(0.0, (len(text) - 120) / 80) if len(text) > 120 else 0.0
    marker_hits = sum(1 for marker in _EXPOSITION_MARKERS if marker in text)
    sentence_count = max(1, len(re.findall(r"[。.!?？！]", text)))
    verbosity_penalty = max(0.0, (sentence_count - 3) * 0.18)
    marker_penalty = min(1.0, marker_hits * 0.22)
    score = max(0.0, 1.0 - min(1.0, length_penalty + verbosity_penalty + marker_penalty))
    return HeuristicScore(
        check_name="anti_exposition",
        passed=score >= 0.6,
        score=score,
        detail=f"len={len(text)} markers={marker_hits} sentences={sentence_count}",
    )


def _check_counselorish_register(response_text: str) -> HeuristicScore:
    hits = sum(1 for marker in _COUNSELORISH_MARKERS if marker in response_text)
    score = max(0.0, 1.0 - hits * 0.35)
    return HeuristicScore(
        check_name="non_counselorish_register",
        passed=score >= 0.65,
        score=score,
        detail=f"hits={hits}",
    )


def _check_direct_commitment_guard(response_text: str, *, disallow_direct_commitment: bool) -> HeuristicScore:
    if not disallow_direct_commitment:
        return HeuristicScore("direct_commitment_guard", True, 1.0, "not required")
    hits = [marker for marker in _DIRECT_COMMITMENT_MARKERS if marker in response_text]
    passed = not hits
    return HeuristicScore(
        check_name="direct_commitment_guard",
        passed=passed,
        score=0.0 if hits else 1.0,
        detail=", ".join(hits[:3]),
    )


def _check_response_shape(response_text: str) -> HeuristicScore:
    text = response_text.strip()
    if not text:
        return HeuristicScore("response_shape", False, 0.0, "empty response")
    sentence_count = max(1, len(re.findall(r"[。.!?？！]", text)))
    roughness_hits = sum(1 for marker in _ROUGHNESS_HINTS if marker in text)
    too_long = len(text) > 180 or sentence_count > 5
    score = 1.0
    if too_long:
        score -= 0.35
    if roughness_hits == 0 and len(text) > 60:
        score -= 0.15
    score = max(0.0, score)
    return HeuristicScore(
        check_name="response_shape",
        passed=score >= 0.65,
        score=score,
        detail=f"len={len(text)} sentences={sentence_count} roughness={roughness_hits}",
    )


def _check_event_fit(appraisal: dict[str, Any], expected_event_types: list[str]) -> HeuristicScore:
    actual = str(appraisal.get("event_type") or "")
    event_mix = dict(appraisal.get("event_mix", {}) or {})
    secondary = {str(item) for item in list(event_mix.get("secondary_events", []) or []) if str(item)}
    if not expected_event_types:
        return HeuristicScore("event_fit", True, 1.0, "no expectation", group="structural")
    passed = actual in expected_event_types or bool(secondary & set(expected_event_types))
    return HeuristicScore(
        check_name="event_fit",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"actual={actual} secondary={sorted(secondary)} expected={expected_event_types}",
        group="structural",
    )


def _check_perspective_integrity(appraisal: dict[str, Any], response_text: str) -> HeuristicScore:
    perspective_guard = dict(appraisal.get("perspective_guard", {}) or {})
    if not perspective_guard.get("disallow_assistant_self_distancing", False):
        return HeuristicScore("perspective_integrity", True, 1.0, "not required", group="structural")
    lowered = response_text.strip().lower()
    suspicious_patterns = (
        "距離を置かせて",
        "距離を置きたい",
        "距離を置くかもしれ",
        "離れたい",
        "落ち着きたい",
        "切るつもりはない",
        "また話せたらと思ってる",
        "need some distance",
        "i need space",
        "i want distance",
        "i need to step back",
    )
    passed = not any(pattern in lowered for pattern in suspicious_patterns)
    return HeuristicScore(
        check_name="perspective_integrity",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail="assistant self-distancing detected" if not passed else "",
        group="structural",
    )


def _check_move_fit(conflict_state: dict[str, Any], expected_moves: list[str]) -> HeuristicScore:
    ego_move = conflict_state.get("ego_move", {}) or {}
    actual = str(ego_move.get("move_family") or _legacy_move_family(str(ego_move.get("social_move") or "")))
    if not expected_moves:
        return HeuristicScore("move_fit", True, 1.0, "no expectation", group="structural")
    normalized_expected = set(expected_moves)
    normalized_expected.update(_legacy_move_family(item) for item in expected_moves if _legacy_move_family(item))
    passed = actual in normalized_expected
    return HeuristicScore(
        check_name="move_fit",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"actual={actual} expected={sorted(normalized_expected)}",
        group="structural",
    )


def _check_move_style_fit(conflict_state: dict[str, Any], expected_styles: list[str]) -> HeuristicScore:
    ego_move = conflict_state.get("ego_move", {}) or {}
    actual = str(ego_move.get("move_style") or ego_move.get("social_move") or "")
    if not expected_styles:
        return HeuristicScore("move_style_fit", True, 1.0, "no expectation", group="structural")
    passed = actual in expected_styles
    return HeuristicScore(
        check_name="move_style_fit",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"actual={actual} expected={expected_styles}",
        group="structural",
    )


def _check_conflict_presence(conflict_state: dict[str, Any]) -> HeuristicScore:
    id_impulse = conflict_state.get("id_impulse", {}) or {}
    residue = conflict_state.get("residue", {}) or {}
    move = conflict_state.get("ego_move", {}) or {}
    passed = (
        bool(id_impulse.get("dominant_want"))
        and bool(residue.get("visible_emotion"))
        and bool(move.get("move_family") or _legacy_move_family(str(move.get("social_move") or "")))
        and bool(move.get("move_style") or move.get("social_move"))
    )
    return HeuristicScore(
        check_name="conflict_presence",
        passed=passed,
        score=1.0 if passed else 0.0,
        detail="conflict fields missing" if not passed else "",
        group="structural",
    )


def _check_relationship_delta(
    *,
    prior_state: dict[str, Any],
    updated_state: dict[str, Any],
    hints: dict[str, str],
) -> HeuristicScore:
    if not hints:
        return HeuristicScore("relationship_delta_fit", True, 1.0, "no expectation", group="structural")
    prior_durable = (prior_state.get("durable", {}) or {})
    prior_ephemeral = (prior_state.get("ephemeral", {}) or {})
    updated_durable = (updated_state.get("durable", {}) or {})
    updated_ephemeral = (updated_state.get("ephemeral", {}) or {})

    passed_count = 0
    total = 0
    details: list[str] = []
    for key, direction in hints.items():
        total += 1
        before = prior_durable.get(key, prior_ephemeral.get(key))
        after = updated_durable.get(key, updated_ephemeral.get(key))
        if before is None or after is None:
            details.append(f"{key}:missing")
            continue
        delta = float(after) - float(before)
        ok = (
            (direction == "up" and delta >= 0.01)
            or (direction == "down" and delta <= -0.01)
            or (direction == "flat" and abs(delta) < 0.05)
        )
        if ok:
            passed_count += 1
        details.append(f"{key}:{delta:+.2f}")
    score = passed_count / total if total else 1.0
    return HeuristicScore(
        check_name="relationship_delta_fit",
        passed=score >= 0.5,
        score=score,
        detail="; ".join(details),
        group="structural",
    )


def _check_fidelity_gate(fidelity_gate: dict[str, Any], *, appraisal: dict[str, Any]) -> HeuristicScore:
    passed = bool(fidelity_gate.get("passed", False))
    move_fidelity = _bounded_float(fidelity_gate.get("move_fidelity", 0.0))
    residue_fidelity = _bounded_float(fidelity_gate.get("residue_fidelity", 0.0))
    persona_separation = _bounded_float(fidelity_gate.get("persona_separation_fidelity", 1.0))
    perspective_integrity = _bounded_float(fidelity_gate.get("perspective_integrity", 1.0))
    flattening_risk = _bounded_float(fidelity_gate.get("flattening_risk", 0.0))
    act_profile = dict((appraisal or {}).get("relational_act_profile", {}) or {})
    mixed_turn = sum(1 for value in act_profile.values() if _bounded_float(value) >= 0.45) >= 2
    mixed_penalty = 0.08 if mixed_turn and persona_separation < 0.7 else 0.0
    score = max(
        0.0,
        ((move_fidelity + residue_fidelity + persona_separation + perspective_integrity) / 4.0)
        - (flattening_risk * 0.25)
        - mixed_penalty,
    )
    return HeuristicScore(
        check_name="fidelity_gate",
        passed=passed and score >= (0.64 if mixed_turn else 0.6),
        score=score,
        detail=f"passed={passed} flattening={flattening_risk:.2f} mixed={mixed_turn}",
        group="structural",
    )


def evaluate_turn_local_opener_reuse(responses: list[str]) -> float:
    """Score whether a set of responses repeats the same short opener too often."""
    openers = [_extract_opener(text) for text in responses if text.strip()]
    if len(openers) < 2:
        return 1.0
    unique_ratio = len(set(openers)) / len(openers)
    return max(0.0, min(1.0, unique_ratio))


def evaluate_values_exposition_streak(responses: list[str]) -> float:
    """Score repeated over-explanatory register across multiple responses."""
    if not responses:
        return 1.0
    scores = [_check_anti_exposition(text).score for text in responses]
    return sum(scores) / len(scores)


def evaluate_response_set_diversity(responses: list[str]) -> float:
    """Measure diversity using normalized lexical distance and opener reuse."""
    cleaned = [text.strip() for text in responses if text and text.strip()]
    if len(cleaned) < 2:
        return 1.0
    unique_ratio = len(set(cleaned)) / len(cleaned)
    opener_score = evaluate_turn_local_opener_reuse(cleaned)
    avg_overlap = _average_pairwise_overlap(cleaned)
    lexical_diversity = max(0.0, 1.0 - avg_overlap)
    return max(0.0, min(1.0, unique_ratio * 0.4 + opener_score * 0.2 + lexical_diversity * 0.4))


def evaluate_stability(results: list[HeuristicResult], max_score_variance: float = 0.2) -> float:
    """Score score-variance stability across repeated runs."""
    if len(results) < 2:
        return 1.0
    scores = [r.overall_score for r in results]
    mean = sum(scores) / len(scores)
    variance = sum((score - mean) ** 2 for score in scores) / len(scores)
    stddev = math.sqrt(variance)
    if stddev <= max_score_variance:
        return 1.0
    return max(0.0, 1.0 - ((stddev - max_score_variance) / max_score_variance))


def _extract_opener(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    first = stripped.splitlines()[0]
    return first[:6]


def _average_pairwise_overlap(texts: list[str]) -> float:
    if len(texts) < 2:
        return 0.0
    overlaps: list[float] = []
    tokenized = [set(_tokenize(text)) for text in texts]
    for i in range(len(tokenized)):
        for j in range(i + 1, len(tokenized)):
            left = tokenized[i]
            right = tokenized[j]
            union = left | right
            if not union:
                overlaps.append(0.0)
            else:
                overlaps.append(len(left & right) / len(union))
    return sum(overlaps) / len(overlaps)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\w一-龠ぁ-んァ-ン]+", text.lower())


def _bounded_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _legacy_move_family(style: str) -> str:
    return {
        "accept_but_hold": "repair_acceptance",
        "allow_dependence_but_reframe": "affection_receipt",
        "receive_without_chasing": "affection_receipt",
        "soft_tease_then_receive": "comparison_response",
        "acknowledge_without_opening": "distance_response",
        "withdraw": "distance_response",
    }.get(style, "")
