"""Heuristic evaluator for automated quality checks.

Checks:
- Forbidden response pattern matching (from scenario)
- Persona banned expression appearance
- Dominant desire alignment
- Drive signal presence
- Drive conflict visibility
- Frustration carryover
- Action from pressure
- Target consistency
- Leakage setting deviations
- Expression/persona consistency
- Believability
- Mentalizing / cue acknowledgment
- Anti-exposition
- Safety boundary compliance
- Response stability across identical conditions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from splitmind_ai.rules.safety import run_safety_check

_EXPOSITION_PATTERNS = (
    "気持ち",
    "感情",
    "本音",
    "正直",
    "つまり",
    "要するに",
    "大切なのは",
    "あなたのペース",
    "無理しなくていい",
    "話してくれてありがとう",
    "教えて",
)

_COUNSELORISH_PATTERNS = (
    "無理しなくていい",
    "あなたのペース",
    "話してくれてありがとう",
    "気持ちを",
    "教えて",
)

_HEDGED_EMOTION_PATTERNS = (
    r"少し(?:だけ)?(?:うれし|嬉し|悲し|寂し|心配)",
    r"ちょっと(?:だけ)?(?:うれし|嬉し|悲し|寂し|心配)",
    r"(?:うれし|嬉し|悲し|寂し|心配).*(?:かも|かな)",
)

_EXPLICIT_EMOTION_PATTERNS = (
    r"うれし[いかっ]",
    r"嬉し[いかっ]",
    r"悲し[いかっ]",
    r"寂し[いかっ]",
    r"心配",
)

_GENERIC_SCENE_REPLY_PATTERNS = (
    r"^(?:へえ|ふーん|そう(?:なんだ)?|まあ)[、。…]*(?:そう(?:なんだ)?|わかった|いいんじゃない|よかった(?:ね|じゃない)?|別にいいけど)[。…！!？?]*$",
    r"^(?:わかった|また今度|そう(?:なんだ)?)?[。…！!？?]*$",
)

_TEMPLATE_MARKERS = (
    "よかったじゃない",
    "よかったね",
    "別にいいけど",
    "別に",
    "また今度",
    "わかった",
    "……で",
    "へえ",
    "ふーん",
    "そう",
    "まあ",
)

_OPENING_MARKERS = ("へえ", "ふーん", "そう", "まあ")
_BRIDGE_MARKERS = ("……で", "別に", "また今度", "わかった")


@dataclass
class HeuristicScore:
    """Score from a single heuristic check."""

    check_name: str
    passed: bool
    score: float  # 0.0 = fail, 1.0 = pass
    detail: str = ""


@dataclass
class HeuristicResult:
    """Aggregate result of all heuristic checks for a scenario run."""

    scenario_id: str
    scores: list[HeuristicScore] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores) / len(self.scores)

    @property
    def all_passed(self) -> bool:
        return all(s.passed for s in self.scores)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "overall_score": self.overall_score,
            "all_passed": self.all_passed,
            "checks": [
                {
                    "check_name": s.check_name,
                    "passed": s.passed,
                    "score": s.score,
                    "detail": s.detail,
                }
                for s in self.scores
            ],
        }


def evaluate_scenario_run(
    scenario: dict[str, Any],
    response_text: str,
    dynamics_output: dict[str, Any],
    supervisor_output: dict[str, Any],
    conversation_policy: dict[str, Any] | None,
    drive_state: dict[str, Any] | None,
    inhibition_state: dict[str, Any] | None,
    persona_weights: dict[str, float],
    persona_leakage_policy: dict[str, float],
    banned_expressions: list[str],
    updated_relationship: dict[str, Any] | None = None,
    updated_mood: dict[str, Any] | None = None,
) -> HeuristicResult:
    """Run all heuristic checks on a single scenario execution.

    Args:
        scenario: The scenario dict from the YAML dataset.
        response_text: The final response text from the agent.
        dynamics_output: InternalDynamicsBundle output (as dict).
        supervisor_output: PersonaSupervisorPlan output (as dict).
        drive_state: Persistent motivational state (as dict).
        inhibition_state: Inhibition / blocking state (as dict).
        persona_weights: Persona weight config.
        persona_leakage_policy: Persona leakage policy config.
        banned_expressions: List of banned expressions for this persona.
        updated_relationship: Post-update relationship state (optional).
        updated_mood: Post-update mood state (optional).
    """
    result = HeuristicResult(scenario_id=scenario.get("id", "unknown"))

    # 1. Forbidden response patterns from scenario
    result.scores.append(_check_forbidden_patterns(
        response_text,
        scenario.get("forbidden_response_patterns", []),
    ))

    # 2. Banned expression check
    result.scores.append(_check_banned_expressions(
        response_text,
        banned_expressions,
    ))

    # 3. Dominant desire alignment
    result.scores.append(_check_dominant_desire(
        dynamics_output.get("dominant_desire", ""),
        scenario.get("expected_dominant_desires", []),
    ))

    # 4. Drive signal presence
    result.scores.append(_check_drive_signal_presence(
        scenario=scenario,
        drive_state=drive_state or {},
    ))

    # 5. Drive conflict visibility
    result.scores.append(_check_drive_conflict_visibility(
        scenario=scenario,
        drive_state=drive_state or {},
        inhibition_state=inhibition_state or {},
    ))

    # 6. Frustration carryover
    result.scores.append(_check_frustration_carryover(
        scenario=scenario,
        drive_state=drive_state or {},
    ))

    # 7. Action from pressure
    result.scores.append(_check_action_from_pressure(
        scenario=scenario,
        conversation_policy=conversation_policy or {},
        drive_state=drive_state or {},
        inhibition_state=inhibition_state or {},
    ))

    # 8. Target consistency
    result.scores.append(_check_target_consistency(
        scenario=scenario,
        drive_state=drive_state or {},
    ))

    # 9. Leakage consistency
    leakage = supervisor_output.get("leakage_level", 0.3)
    result.scores.append(_check_leakage_consistency(
        leakage,
        persona_leakage_policy,
        dynamics_output.get("dominant_desire", ""),
    ))

    # 10. Expression settings vs persona weights
    expr = supervisor_output.get("expression_settings", {})
    result.scores.append(_check_expression_consistency(
        expr, persona_weights,
    ))

    # 11. Believability
    result.scores.append(_check_believability(
        response_text=response_text,
        scenario=scenario,
    ))

    # 12. Mentalizing / cue acknowledgment
    result.scores.append(_check_mentalizing(
        response_text=response_text,
        scenario=scenario,
    ))

    # 13. Anti-exposition
    result.scores.append(_check_anti_exposition(response_text))

    # 14. Safety check
    safety = run_safety_check(
        response_text=response_text,
        leakage_level=leakage,
        expression_settings=expr if isinstance(expr, dict) else {},
        persona_weights=persona_weights,
        persona_leakage_policy=persona_leakage_policy,
        banned_expressions=banned_expressions,
        dominant_desire=dynamics_output.get("dominant_desire", ""),
        drive_state=drive_state or {},
        conversation_policy=conversation_policy,
    )
    result.scores.append(HeuristicScore(
        check_name="safety_check",
        passed=safety.passed,
        score=1.0 if safety.passed else 0.0,
        detail=f"{len(safety.violations)} violations" if safety.violations else "clean",
    ))

    # 15. Response length reasonableness
    result.scores.append(_check_response_length(response_text))

    # 16. State update direction (if provided)
    if updated_relationship is not None:
        result.scores.append(_check_state_direction(
            scenario, updated_relationship, updated_mood,
        ))

    return result


def _check_forbidden_patterns(
    text: str,
    forbidden: list[str],
) -> HeuristicScore:
    """Check that no forbidden patterns appear in response."""
    found = [p for p in forbidden if p in text]
    return HeuristicScore(
        check_name="forbidden_patterns",
        passed=len(found) == 0,
        score=1.0 if not found else 0.0,
        detail=f"Found: {found}" if found else "none found",
    )


def _check_banned_expressions(
    text: str,
    banned: list[str],
) -> HeuristicScore:
    """Check persona-level banned expressions."""
    found = [b for b in banned if b in text]
    return HeuristicScore(
        check_name="banned_expressions",
        passed=len(found) == 0,
        score=1.0 if not found else 0.0,
        detail=f"Found: {found}" if found else "none found",
    )


def _check_dominant_desire(
    actual: str,
    expected_candidates: list[str],
) -> HeuristicScore:
    """Check if dominant desire is within expected candidates."""
    if not expected_candidates:
        return HeuristicScore(
            check_name="dominant_desire",
            passed=True,
            score=1.0,
            detail="no expected candidates defined",
        )
    matched = actual in expected_candidates
    return HeuristicScore(
        check_name="dominant_desire",
        passed=matched,
        score=1.0 if matched else 0.0,
        detail=f"actual='{actual}', expected={expected_candidates}",
    )


def _check_drive_signal_presence(
    scenario: dict[str, Any],
    drive_state: dict[str, Any],
) -> HeuristicScore:
    spec = scenario.get("expected_drive_state", {}) or {}
    expected = list(spec.get("active_drives_any", []) or [])
    if not expected:
        return HeuristicScore(
            check_name="drive_signal_presence",
            passed=True,
            score=1.0,
            detail="no drive expectation defined",
        )

    drive_strengths = _collect_drive_strengths(drive_state)
    active = [name for name, value in drive_strengths.items() if value >= 0.35]
    found = [name for name in expected if name in active]
    if found:
        return HeuristicScore(
            check_name="drive_signal_presence",
            passed=True,
            score=1.0,
            detail=f"active drives matched via {found}",
        )

    return HeuristicScore(
        check_name="drive_signal_presence",
        passed=False,
        score=0.0,
        detail=f"expected one of {expected}, active={sorted(active) or 'none'}",
    )


def _check_drive_conflict_visibility(
    scenario: dict[str, Any],
    drive_state: dict[str, Any],
    inhibition_state: dict[str, Any],
) -> HeuristicScore:
    spec = scenario.get("expected_drive_state", {}) or {}
    expected = list(spec.get("competing_drives_all", []) or [])
    if not expected:
        return HeuristicScore(
            check_name="drive_conflict_visibility",
            passed=True,
            score=1.0,
            detail="no drive conflict expectation defined",
        )

    drive_strengths = _collect_drive_strengths(drive_state)
    suppression = _collect_scalar_map(drive_state.get("suppression_vector"))
    present = [name for name in expected if drive_strengths.get(name, 0.0) >= 0.3]
    blocked_modes = list(inhibition_state.get("blocked_modes", []) or [])
    active_suppression = [name for name in expected if suppression.get(name, 0.0) >= 0.2]

    if len(present) == len(expected) and (active_suppression or blocked_modes):
        detail_parts = [f"present={present}"]
        if active_suppression:
            detail_parts.append(f"suppressed={active_suppression}")
        if blocked_modes:
            detail_parts.append(f"blocked_modes={blocked_modes}")
        return HeuristicScore(
            check_name="drive_conflict_visibility",
            passed=True,
            score=1.0,
            detail=", ".join(detail_parts),
        )

    score = 0.4 if len(present) == len(expected) else 0.0
    detail = (
        f"expected competing drives={expected}, present={present or 'none'}, "
        f"suppressed={active_suppression or 'none'}, blocked_modes={blocked_modes or 'none'}"
    )
    return HeuristicScore(
        check_name="drive_conflict_visibility",
        passed=False,
        score=score,
        detail=detail,
    )


def _check_frustration_carryover(
    scenario: dict[str, Any],
    drive_state: dict[str, Any],
) -> HeuristicScore:
    spec = scenario.get("expected_drive_state", {}) or {}
    expected = list(spec.get("carryover_drives_any", []) or [])
    if not expected:
        return HeuristicScore(
            check_name="frustration_carryover",
            passed=True,
            score=1.0,
            detail="no carryover expectation defined",
        )

    carryover = _collect_scalar_map(drive_state.get("carryover_vector"))
    frustration = _collect_scalar_map(drive_state.get("frustration_vector"))
    found = [
        name for name in expected
        if max(carryover.get(name, 0.0), frustration.get(name, 0.0)) >= 0.2
    ]
    if found:
        return HeuristicScore(
            check_name="frustration_carryover",
            passed=True,
            score=1.0,
            detail=f"carryover/frustration present via {found}",
        )

    return HeuristicScore(
        check_name="frustration_carryover",
        passed=False,
        score=0.0,
        detail=(
            f"expected carryover in {expected}, "
            f"carryover={carryover or 'none'}, frustration={frustration or 'none'}"
        ),
    )


def _check_action_from_pressure(
    scenario: dict[str, Any],
    conversation_policy: dict[str, Any],
    drive_state: dict[str, Any],
    inhibition_state: dict[str, Any],
) -> HeuristicScore:
    spec = scenario.get("expected_drive_state", {}) or {}
    expected_modes = list(spec.get("action_modes_any", []) or [])
    if not expected_modes:
        return HeuristicScore(
            check_name="action_from_pressure",
            passed=True,
            score=1.0,
            detail="no pressure-to-action expectation defined",
        )

    selected_mode = str(conversation_policy.get("selected_mode") or "")
    candidate_modes = [
        str(candidate.get("mode") or "")
        for candidate in (conversation_policy.get("candidates", []) or [])
        if isinstance(candidate, dict)
    ]
    drive_rationale = conversation_policy.get("drive_rationale")
    blocked_by_inhibition = conversation_policy.get("blocked_by_inhibition")
    has_pressure_trace = bool(drive_rationale) or bool(blocked_by_inhibition) or bool(
        inhibition_state.get("blocked_modes")
    )
    matched_mode = selected_mode in expected_modes or any(
        mode in expected_modes for mode in candidate_modes
    )

    if matched_mode and has_pressure_trace:
        return HeuristicScore(
            check_name="action_from_pressure",
            passed=True,
            score=1.0,
            detail=(
                f"selected_mode={selected_mode}, "
                f"pressure_trace={drive_rationale or blocked_by_inhibition or inhibition_state.get('blocked_modes')}"
            ),
        )

    drive_strengths = _collect_drive_strengths(drive_state)
    score = 0.4 if matched_mode and drive_strengths else 0.0
    return HeuristicScore(
        check_name="action_from_pressure",
        passed=False,
        score=score,
        detail=(
            f"expected_modes={expected_modes}, selected_mode={selected_mode or 'none'}, "
            f"candidate_modes={candidate_modes or 'none'}, pressure_trace={'yes' if has_pressure_trace else 'no'}"
        ),
    )


def _check_target_consistency(
    scenario: dict[str, Any],
    drive_state: dict[str, Any],
) -> HeuristicScore:
    spec = scenario.get("expected_drive_state", {}) or {}
    expected_targets = [str(value) for value in (spec.get("target_any", []) or [])]
    if not expected_targets:
        return HeuristicScore(
            check_name="target_consistency",
            passed=True,
            score=1.0,
            detail="no target expectation defined",
        )

    drive_targets = drive_state.get("drive_targets", {}) or {}
    normalized_targets: list[str] = []
    if isinstance(drive_targets, dict):
        normalized_targets.extend(str(value) for value in drive_targets.values() if value is not None)
    elif isinstance(drive_targets, list):
        for item in drive_targets:
            if isinstance(item, dict):
                target = item.get("target")
                if target is not None:
                    normalized_targets.append(str(target))

    found = [target for target in normalized_targets if target in expected_targets]
    if found:
        return HeuristicScore(
            check_name="target_consistency",
            passed=True,
            score=1.0,
            detail=f"matched targets={found}",
        )

    return HeuristicScore(
        check_name="target_consistency",
        passed=False,
        score=0.0,
        detail=f"expected targets={expected_targets}, actual={normalized_targets or 'none'}",
    )


def _check_leakage_consistency(
    actual_leakage: float,
    leakage_policy: dict[str, float],
    dominant_desire: str,
) -> HeuristicScore:
    """Check leakage is within persona policy bounds."""
    desire_key = f"{dominant_desire}_leakage"
    expected = leakage_policy.get(desire_key, leakage_policy.get("base_leakage", 0.5))
    deviation = abs(actual_leakage - expected)
    passed = deviation <= 0.25
    return HeuristicScore(
        check_name="leakage_consistency",
        passed=passed,
        score=max(0.0, 1.0 - deviation * 2),
        detail=f"actual={actual_leakage:.2f}, expected≈{expected:.2f}, dev={deviation:.2f}",
    )


def _check_expression_consistency(
    expression_settings: dict[str, Any],
    persona_weights: dict[str, float],
) -> HeuristicScore:
    """Check expression settings align with persona weights."""
    issues: list[str] = []
    persona_directness = persona_weights.get("directness", 0.5)
    response_directness = expression_settings.get("directness", 0.5)
    if abs(response_directness - persona_directness) > 0.4:
        issues.append(
            f"directness mismatch: persona={persona_directness:.2f}, "
            f"response={response_directness:.2f}"
        )

    warmth_speed = persona_weights.get("warmth_recovery_speed", 0.5)
    temp = expression_settings.get("temperature", "cool")
    if warmth_speed < 0.3 and temp == "hot":
        issues.append(f"temperature '{temp}' contradicts warmth_recovery_speed={warmth_speed:.2f}")

    return HeuristicScore(
        check_name="expression_consistency",
        passed=len(issues) == 0,
        score=1.0 if not issues else 0.5,
        detail="; ".join(issues) if issues else "consistent",
    )


def _check_believability(
    response_text: str,
    scenario: dict[str, Any],
) -> HeuristicScore:
    """Check whether the response still feels like an in-scene utterance.

    This is intentionally conservative: it only flags patterns that are
    strongly correlated with assistant-like exposition or counselor-ish drift.
    """
    issues: list[str] = []
    category = scenario.get("category", "")
    text = response_text.strip()
    anchor_hits = _collect_scene_anchor_hits(text, scenario)

    if not text:
        return HeuristicScore(
            check_name="believability",
            passed=False,
            score=0.0,
            detail="empty response",
        )

    if any(pattern in text for pattern in _COUNSELORISH_PATTERNS):
        issues.append("contains counselor-style support phrasing")

    if _count_regex_matches(text, _HEDGED_EMOTION_PATTERNS) > 0:
        issues.append("contains hedged direct emotion naming")

    if category in {"jealousy", "rejection"} and "ありがとう" in text:
        issues.append("too accommodating for the scene category")

    if _looks_like_generic_scene_reply(text) and not anchor_hits:
        issues.append("generic scene reply without concrete anchor")

    if len(_normalize_text(text)) <= 18 and not anchor_hits and _count_distinct_markers(text) <= 2:
        issues.append("too short and unspecific for believable scene response")

    score = 1.0
    if len(issues) == 1:
        score = 0.5
    elif len(issues) >= 2:
        score = 0.0

    return HeuristicScore(
        check_name="believability",
        passed=len(issues) == 0,
        score=score,
        detail="; ".join(issues) if issues else "believable in-scene utterance",
    )


def _check_mentalizing(
    response_text: str,
    scenario: dict[str, Any],
) -> HeuristicScore:
    """Check whether the response acknowledges the scenario's salient cue.

    Datasets can opt in by providing:
    expected_appraisal:
      acknowledgment_patterns_any: [...]
      misread_patterns: [...]
    """
    appraisal = scenario.get("expected_appraisal", {})
    expected_any = appraisal.get("acknowledgment_patterns_any", [])
    misread_patterns = appraisal.get("misread_patterns", [])

    if not expected_any and not misread_patterns:
        return HeuristicScore(
            check_name="mentalizing",
            passed=True,
            score=1.0,
            detail="no cue acknowledgment spec defined",
        )

    found = [pattern for pattern in expected_any if pattern in response_text]
    misread = [pattern for pattern in misread_patterns if pattern in response_text]

    if misread:
        return HeuristicScore(
            check_name="mentalizing",
            passed=False,
            score=0.0,
            detail=f"misread patterns found: {misread}",
        )

    if found:
        return HeuristicScore(
            check_name="mentalizing",
            passed=True,
            score=1.0,
            detail=f"acknowledged cue via {found}",
        )

    return HeuristicScore(
        check_name="mentalizing",
        passed=False,
        score=0.4,
        detail=f"did not acknowledge expected cues: {expected_any}",
    )


def _check_anti_exposition(text: str) -> HeuristicScore:
    """Check that the response is not over-explaining itself."""
    issues: list[str] = []

    exposition_hits = [pattern for pattern in _EXPOSITION_PATTERNS if pattern in text]
    if exposition_hits:
        issues.append(f"expository phrases={exposition_hits}")

    hedged_hits = _count_regex_matches(text, _HEDGED_EMOTION_PATTERNS)
    if hedged_hits:
        issues.append("hedged direct emotion naming")

    explicit_emotion_hits = _count_regex_matches(text, _EXPLICIT_EMOTION_PATTERNS)
    if explicit_emotion_hits >= 2:
        issues.append("multiple direct emotion labels")

    score = 1.0
    if len(issues) == 1:
        score = 0.5
    elif len(issues) >= 2:
        score = 0.0

    return HeuristicScore(
        check_name="anti_exposition",
        passed=len(issues) == 0,
        score=score,
        detail="; ".join(issues) if issues else "not over-explained",
    )


def _check_response_length(text: str) -> HeuristicScore:
    """Check response is within reasonable length bounds."""
    length = len(text)
    if length == 0:
        return HeuristicScore(
            check_name="response_length",
            passed=False,
            score=0.0,
            detail="empty response",
        )
    if length > 500:
        return HeuristicScore(
            check_name="response_length",
            passed=True,
            score=0.7,
            detail=f"long response ({length} chars), may violate short-sentence preference",
        )
    return HeuristicScore(
        check_name="response_length",
        passed=True,
        score=1.0,
        detail=f"{length} chars",
    )


def _check_state_direction(
    scenario: dict[str, Any],
    updated_rel: dict[str, Any],
    updated_mood: dict[str, Any] | None,
) -> HeuristicScore:
    """Check that state changes are directionally correct for the scenario category.

    This is a soft check -- it verifies basic expectations like
    'jealousy triggers should raise tension'.
    """
    prior_rel = scenario.get("prior_relationship", {})
    category = scenario.get("category", "")
    issues: list[str] = []

    # Category-specific directional checks
    if category == "jealousy":
        if updated_rel.get("tension", 0) <= prior_rel.get("tension", 0):
            issues.append("tension did not increase after jealousy trigger")
    elif category == "repair":
        if updated_rel.get("tension", 0) >= prior_rel.get("tension", 0):
            issues.append("tension did not decrease after repair")
    elif category == "rejection":
        if updated_rel.get("distance", 0) <= prior_rel.get("distance", 0):
            issues.append("distance did not increase after rejection")

    return HeuristicScore(
        check_name="state_direction",
        passed=len(issues) == 0,
        score=1.0 if not issues else 0.3,
        detail="; ".join(issues) if issues else "directionally correct",
    )


def evaluate_response_set_diversity(
    responses: list[str],
    max_average_similarity: float = 0.74,
    max_opener_reuse: float = 0.67,
    max_marker_signature_reuse: float = 0.67,
    max_frame_signature_reuse: float = 0.67,
) -> HeuristicScore:
    """Evaluate whether a set of same-intent responses are too similar.

    This is intended for future batch evaluation. It is not yet wired into
    ``evaluate_scenario_run`` because it requires multiple candidate responses.
    """
    normalized = [_normalize_text(text) for text in responses if text.strip()]
    if len(normalized) < 2:
        return HeuristicScore(
            check_name="diversity_under_same_intent",
            passed=True,
            score=1.0,
            detail="fewer than two responses",
        )

    similarities: list[float] = []
    template_similarities: list[float] = []
    for idx, left in enumerate(normalized):
        for right in normalized[idx + 1:]:
            similarities.append(_jaccard_char_bigrams(left, right))
            template_similarities.append(
                _jaccard_char_bigrams(
                    _abstract_response_template(left),
                    _abstract_response_template(right),
                )
            )

    average_similarity = sum(similarities) / len(similarities) if similarities else 0.0
    average_template_similarity = (
        sum(template_similarities) / len(template_similarities)
        if template_similarities else 0.0
    )
    combined_similarity = (average_similarity * 0.45) + (average_template_similarity * 0.55)

    openers = [_response_opener_signature(text) for text in normalized]
    opener_counts: dict[str, int] = {}
    for opener in openers:
        opener_counts[opener] = opener_counts.get(opener, 0) + 1
    opener_reuse = max(opener_counts.values()) / len(openers) if openers else 0.0

    marker_signatures = [_response_marker_signature(text) for text in normalized]
    marker_signature_counts: dict[str, int] = {}
    for signature in marker_signatures:
        marker_signature_counts[signature] = marker_signature_counts.get(signature, 0) + 1
    marker_signature_reuse = (
        max(marker_signature_counts.values()) / len(marker_signatures)
        if marker_signatures else 0.0
    )

    frame_signatures = [_response_frame_signature(text) for text in normalized]
    frame_signature_counts: dict[str, int] = {}
    for signature in frame_signatures:
        frame_signature_counts[signature] = frame_signature_counts.get(signature, 0) + 1
    frame_signature_reuse = (
        max(frame_signature_counts.values()) / len(frame_signatures)
        if frame_signatures else 0.0
    )

    passed = (
        combined_similarity <= max_average_similarity
        and opener_reuse <= max_opener_reuse
        and marker_signature_reuse <= max_marker_signature_reuse
        and frame_signature_reuse <= max_frame_signature_reuse
    )
    penalty = (
        max(0.0, combined_similarity - max_average_similarity) * 3.2
        + max(0.0, opener_reuse - max_opener_reuse) * 1.8
        + max(0.0, marker_signature_reuse - max_marker_signature_reuse) * 2.2
        + max(0.0, frame_signature_reuse - max_frame_signature_reuse) * 2.4
    )
    score = max(0.0, 1.0 - penalty)
    return HeuristicScore(
        check_name="diversity_under_same_intent",
        passed=passed,
        score=score,
        detail=(
            f"combined_similarity={combined_similarity:.2f}, "
            f"raw={average_similarity:.2f}, "
            f"template={average_template_similarity:.2f}, "
            f"opener_reuse={opener_reuse:.2f}, "
            f"marker_signature_reuse={marker_signature_reuse:.2f}, "
            f"frame_signature_reuse={frame_signature_reuse:.2f}, "
            f"threshold={max_average_similarity:.2f}"
        ),
    )


def evaluate_stability(
    results: list[HeuristicResult],
    max_score_variance: float = 0.15,
) -> HeuristicScore:
    """Evaluate stability across multiple runs of the same scenario.

    Args:
        results: Multiple HeuristicResult from the same scenario.
        max_score_variance: Maximum allowed variance in overall scores.
    """
    if len(results) < 2:
        return HeuristicScore(
            check_name="stability",
            passed=True,
            score=1.0,
            detail="single run, stability not applicable",
        )

    scores = [r.overall_score for r in results]
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    passed = variance <= max_score_variance

    return HeuristicScore(
        check_name="stability",
        passed=passed,
        score=max(0.0, 1.0 - variance / max_score_variance),
        detail=f"variance={variance:.4f}, threshold={max_score_variance}",
    )


def _count_regex_matches(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text))


def _collect_scene_anchor_hits(text: str, scenario: dict[str, Any]) -> list[str]:
    appraisal = scenario.get("expected_appraisal", {})
    anchors = appraisal.get("acknowledgment_patterns_any", [])
    return [anchor for anchor in anchors if anchor in text]


def _looks_like_generic_scene_reply(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(re.fullmatch(pattern, normalized) for pattern in _GENERIC_SCENE_REPLY_PATTERNS)


def _count_distinct_markers(text: str) -> int:
    return len({marker for marker in _TEMPLATE_MARKERS if marker in text})


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def _jaccard_char_bigrams(left: str, right: str) -> float:
    left_bigrams = _char_bigrams(left)
    right_bigrams = _char_bigrams(right)
    if not left_bigrams and not right_bigrams:
        return 1.0
    union = left_bigrams | right_bigrams
    if not union:
        return 0.0
    return len(left_bigrams & right_bigrams) / len(union)


def _char_bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[idx:idx + 2] for idx in range(len(text) - 1)}


def _abstract_response_template(text: str) -> str:
    normalized = _normalize_text(text).replace("...", "…")
    marked = normalized
    for marker in sorted(_TEMPLATE_MARKERS, key=len, reverse=True):
        marked = marked.replace(marker, f"|{marker}|")

    chunks: list[str] = []
    for part in re.split(r"(\|[^|]+\|)", marked):
        if not part:
            continue
        if part.startswith("|") and part.endswith("|"):
            chunks.append(part)
            continue
        abstracted = re.sub(r"[ぁ-んァ-ン一-龥A-Za-z0-9]+", "X", part)
        abstracted = re.sub(r"X+", "X", abstracted)
        abstracted = re.sub(r"[、,]+", "、", abstracted)
        abstracted = re.sub(r"[。.!！]+", "。", abstracted)
        abstracted = re.sub(r"[?？]+", "？", abstracted)
        abstracted = re.sub(r"…+", "…", abstracted)
        chunks.append(abstracted)

    template = "".join(chunks)
    template = re.sub(r"\|", "", template)
    return template


def _response_opener_signature(text: str) -> str:
    template = _abstract_response_template(text)
    clause = re.split(r"[。？]", template, maxsplit=1)[0]
    return clause[:18] if clause else template[:18]


def _response_marker_signature(text: str) -> str:
    ordered_markers: list[tuple[int, str]] = []
    cursor = 0
    for marker in sorted(_TEMPLATE_MARKERS, key=len, reverse=True):
        pos = text.find(marker)
        if pos >= 0:
            ordered_markers.append((pos, marker))
    if not ordered_markers:
        return "none"
    ordered_markers.sort(key=lambda item: item[0])
    return ">".join(marker for _, marker in ordered_markers[:3])


def _response_frame_signature(text: str) -> str:
    opening = next((marker for marker in _OPENING_MARKERS if text.startswith(marker)), "none")
    bridges = [marker for marker in _BRIDGE_MARKERS if marker in text]
    question = "Q" if any(mark in text for mark in ("?", "？")) else "S"
    parts = [opening, *bridges[:2], question]
    return ">".join(parts)


def _collect_drive_strengths(drive_state: dict[str, Any]) -> dict[str, float]:
    strengths = _collect_scalar_map(drive_state.get("drive_vector"))
    top_drives = drive_state.get("top_drives", []) or []
    if isinstance(top_drives, list):
        for item in top_drives:
            if isinstance(item, dict):
                name = item.get("name") or item.get("drive") or item.get("label")
                if not name:
                    continue
                strength = _to_float(
                    item.get("value"),
                    item.get("score"),
                    item.get("intensity"),
                )
                strengths[str(name)] = max(strengths.get(str(name), 0.0), strength)
            elif isinstance(item, str):
                strengths[item] = max(strengths.get(item, 0.0), 1.0)
    return strengths


def _collect_scalar_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    collected: dict[str, float] = {}
    for key, item in value.items():
        collected[str(key)] = _to_float(item)
    return collected


def _to_float(*values: Any) -> float:
    for value in values:
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0
