"""Helpers for merging relational cue parses into downstream appraisal state."""

from __future__ import annotations

from typing import Any


def merge_appraisal_with_cue_parse(
    *,
    llm_appraisal: dict[str, Any],
    cue_parse: dict[str, Any],
) -> dict[str, Any]:
    """Merge two LLM-authored structures without semantic keyword overrides."""
    merged = dict(llm_appraisal)

    merged["cues"] = _merge_cues(
        list(cue_parse.get("cues", []) or []),
        list(merged.get("cues", []) or []),
    )
    merged["active_themes"] = list(dict.fromkeys([
        *list(cue_parse.get("active_themes", []) or []),
        *list(merged.get("active_themes", []) or []),
    ]))[:6]

    if not str(merged.get("user_intent_guess") or "").strip():
        merged["user_intent_guess"] = cue_parse.get("user_intent_guess", "")

    merged["event_mix"] = _merge_event_mix(
        cue_parse.get("event_mix", {}),
        merged.get("event_mix", {}),
        merged.get("event_type", "unknown"),
    )
    merged["relational_act_profile"] = _merge_relational_act_profile(
        cue_parse=cue_parse,
        appraisal=merged,
    )
    merged["speaker_intent"] = _merge_structured_block(
        cue_parse.get("speaker_intent", {}),
        merged.get("speaker_intent", {}),
    )
    merged["perspective_guard"] = _merge_structured_block(
        cue_parse.get("perspective_guard", {}),
        merged.get("perspective_guard", {}),
    )

    return merged


def _merge_event_mix(
    cue_mix: dict[str, Any] | None,
    appraisal_mix: dict[str, Any] | None,
    event_type: Any,
) -> dict[str, Any]:
    cue_mix = dict(cue_mix or {})
    appraisal_mix = dict(appraisal_mix or {})

    primary_event = _pick_semantic_label(
        appraisal_mix.get("primary_event"),
        cue_mix.get("primary_event"),
        event_type,
        fallback="unknown",
    )
    secondary_events = list(dict.fromkeys(
        item
        for item in [
            *list(cue_mix.get("secondary_events", []) or []),
            *list(appraisal_mix.get("secondary_events", []) or []),
        ]
        if item and item != primary_event
    ))

    return {
        "primary_event": primary_event,
        "secondary_events": secondary_events,
        "comparison_frame": _pick_semantic_label(
            appraisal_mix.get("comparison_frame"),
            cue_mix.get("comparison_frame"),
            fallback="none",
        ),
        "repair_signal_strength": _max_float(
            cue_mix.get("repair_signal_strength"),
            appraisal_mix.get("repair_signal_strength"),
        ),
        "priority_signal_strength": _max_float(
            cue_mix.get("priority_signal_strength"),
            appraisal_mix.get("priority_signal_strength"),
        ),
        "distance_signal_strength": _max_float(
            cue_mix.get("distance_signal_strength"),
            appraisal_mix.get("distance_signal_strength"),
        ),
    }


def _merge_relational_act_profile(
    *,
    cue_parse: dict[str, Any] | None,
    appraisal: dict[str, Any] | None,
) -> dict[str, float]:
    cue_parse = dict(cue_parse or {})
    appraisal = dict(appraisal or {})
    cue_profile = dict(cue_parse.get("relational_act_profile", {}) or {})
    appraisal_profile = dict(appraisal.get("relational_act_profile", {}) or {})
    event_mix = dict(appraisal.get("event_mix", {}) or {})
    speaker_intent = dict(appraisal.get("speaker_intent", {}) or {})
    event_type = str(appraisal.get("event_type") or "")
    cues = list(appraisal.get("cues", []) or [])

    derived = {
        "affection": 0.0,
        "repair_bid": _max_float(
            event_mix.get("repair_signal_strength"),
            1.0 if speaker_intent.get("user_repair_bid") else 0.0,
        ),
        "reassurance": 0.0,
        "commitment": 1.0 if speaker_intent.get("user_commitment_signal") else 0.0,
        "priority_restore": _max_float(event_mix.get("priority_signal_strength")),
        "comparison": 0.0,
        "distancing": _max_float(
            event_mix.get("distance_signal_strength"),
            1.0 if speaker_intent.get("user_distance_request") else 0.0,
        ),
    }

    if event_type == "affection_signal":
        derived["affection"] = max(derived["affection"], 0.7)
    if event_type == "repair_offer":
        derived["repair_bid"] = max(derived["repair_bid"], 0.8)
    if event_type == "reassurance":
        derived["reassurance"] = max(derived["reassurance"], 0.8)
    if event_type == "commitment_request":
        derived["commitment"] = max(derived["commitment"], 0.75)
    if event_type == "exclusive_disclosure":
        derived["affection"] = max(derived["affection"], 0.55)
        derived["commitment"] = max(derived["commitment"], 0.45)
    if event_type == "provocation":
        derived["comparison"] = max(derived["comparison"], 0.75)
    if event_type == "distancing":
        derived["distancing"] = max(derived["distancing"], 0.9)

    comparison_frame = str(event_mix.get("comparison_frame") or "")
    if comparison_frame and comparison_frame != "none":
        derived["comparison"] = max(derived["comparison"], 0.8)

    cue_labels = {str(item.get("label") or "") for item in cues if isinstance(item, dict)}
    if {"apology", "repair_bid"} & cue_labels:
        derived["repair_bid"] = max(derived["repair_bid"], 0.72)
    if {"reassurance", "commitment_signal"} & cue_labels:
        derived["reassurance"] = max(derived["reassurance"], 0.6)
    if {"comparison_or_priority", "third_party_mention"} & cue_labels:
        derived["comparison"] = max(derived["comparison"], 0.68)
    if {"affection", "exclusive_language"} & cue_labels:
        derived["affection"] = max(derived["affection"], 0.62)
    if {"distancing", "withdrawal"} & cue_labels:
        derived["distancing"] = max(derived["distancing"], 0.8)

    if derived["repair_bid"] >= 0.45:
        derived["reassurance"] = max(derived["reassurance"], min(0.75, derived["repair_bid"] * 0.7))
    if derived["priority_restore"] >= 0.45:
        derived["reassurance"] = max(derived["reassurance"], min(0.7, derived["priority_restore"] * 0.75))
        derived["affection"] = max(derived["affection"], min(0.7, derived["priority_restore"] * 0.65))
    if derived["commitment"] >= 0.45:
        derived["affection"] = max(derived["affection"], min(0.72, derived["commitment"] * 0.75))

    return {
        key: round(_clamp01(_max_float(cue_profile.get(key), appraisal_profile.get(key), value)), 4)
        for key, value in derived.items()
    }


def _merge_structured_block(
    cue_block: dict[str, Any] | None,
    appraisal_block: dict[str, Any] | None,
) -> dict[str, Any]:
    cue_block = dict(cue_block or {})
    appraisal_block = dict(appraisal_block or {})
    merged = dict(cue_block)
    for key, value in appraisal_block.items():
        if _is_meaningful(value):
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    return merged


def _merge_cues(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in [*left, *right]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        previous = merged.get(label)
        if previous is None or _safe_float(item.get("intensity")) >= _safe_float(previous.get("intensity")):
            merged[label] = item
    return list(merged.values())


def _pick_semantic_label(*values: Any, fallback: str) -> str:
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized and normalized not in {"unknown", "none"}:
            return normalized
    return fallback


def _max_float(*values: Any) -> float:
    return max(_safe_float(value) for value in values)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_meaningful(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if value is None:
        return False
    return True
