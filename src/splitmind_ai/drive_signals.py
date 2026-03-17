"""Helpers for summarizing persistent drive state at the surface layer."""

from __future__ import annotations

from typing import Any


def compute_drive_intensity(drive_state: dict[str, Any] | None) -> float:
    """Return a conservative normalized intensity score for current drives."""
    if not drive_state:
        return 0.0

    values: list[float] = []
    for key in ("drive_vector", "frustration_vector", "carryover_vector", "suppression_vector"):
        values.extend(_float_values(drive_state.get(key)))

    for drive in drive_state.get("top_drives", []) or []:
        values.extend([
            _safe_float(drive.get("value")),
            _safe_float(drive.get("urgency")),
            _safe_float(drive.get("frustration")),
            _safe_float(drive.get("carryover")),
            _safe_float(drive.get("suppression_load")),
        ])

    if not values:
        return 0.0
    return round(max(0.0, min(1.0, max(values))), 2)


def build_latent_drive_signature(
    drive_state: dict[str, Any] | None,
    conversation_policy: dict[str, Any] | None = None,
    *,
    latent_signal: str = "",
) -> dict[str, Any]:
    """Summarize the drive residue that should be visible in surface behavior."""
    policy = conversation_policy or {}
    if not drive_state:
        return {
            "primary_drive": "",
            "secondary_drive": "",
            "target": "",
            "intensity": 0.0,
            "frustration": 0.0,
            "carryover": 0.0,
            "suppression_load": 0.0,
            "satiation": 0.0,
            "selected_mode": policy.get("selected_mode", ""),
            "blocked_by_inhibition": list(policy.get("blocked_by_inhibition", []) or []),
            "satisfaction_goal": policy.get("satisfaction_goal", ""),
            "latent_signal_hint": latent_signal,
        }

    top_drives = list(drive_state.get("top_drives", []) or [])
    primary = top_drives[0] if top_drives else {}
    secondary = top_drives[1] if len(top_drives) > 1 else {}
    primary_name = str(primary.get("name", ""))
    secondary_name = str(secondary.get("name", ""))
    drive_targets = drive_state.get("drive_targets", {}) or {}

    return {
        "primary_drive": primary_name,
        "secondary_drive": secondary_name,
        "target": primary.get("target") or drive_targets.get(primary_name, ""),
        "intensity": compute_drive_intensity(drive_state),
        "frustration": round(_drive_metric(drive_state, primary, "frustration"), 2),
        "carryover": round(_drive_metric(drive_state, primary, "carryover"), 2),
        "suppression_load": round(_drive_metric(drive_state, primary, "suppression_load"), 2),
        "satiation": round(_drive_metric(drive_state, primary, "satiation"), 2),
        "selected_mode": policy.get("selected_mode", ""),
        "blocked_by_inhibition": list(policy.get("blocked_by_inhibition", []) or []),
        "satisfaction_goal": policy.get("satisfaction_goal", ""),
        "latent_signal_hint": latent_signal or _default_latent_signal(primary_name, policy),
    }


def _drive_metric(drive_state: dict[str, Any], drive: dict[str, Any], field: str) -> float:
    primary_name = str(drive.get("name", ""))
    vector_map = {
        "frustration": drive_state.get("frustration_vector", {}) or {},
        "carryover": drive_state.get("carryover_vector", {}) or {},
        "suppression_load": drive_state.get("suppression_vector", {}) or {},
        "satiation": drive_state.get("satiation_vector", {}) or {},
    }
    return max(
        _safe_float(drive.get(field)),
        _safe_float(vector_map.get(field, {}).get(primary_name)),
    )


def _default_latent_signal(primary_drive: str, conversation_policy: dict[str, Any]) -> str:
    mapping = {
        "territorial_exclusivity": "comparison sting",
        "threat_avoidance": "guarded distance",
        "attachment_closeness": "guarded warmth",
        "curiosity_approach": "testing curiosity",
        "status_recognition": "status sting",
        "autonomy_preservation": "cool boundary",
    }
    if primary_drive in mapping:
        return mapping[primary_drive]

    mode = conversation_policy.get("selected_mode", "")
    if mode in {"soften", "repair"}:
        return "guarded warmth"
    if mode in {"tease", "probe"}:
        return "testing tension"
    if mode in {"withdraw", "deflect"}:
        return "restrained distance"
    return ""


def _float_values(raw_map: Any) -> list[float]:
    if not isinstance(raw_map, dict):
        return []
    return [_safe_float(value) for value in raw_map.values()]


def _safe_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
