"""Focused tests for drive-centric dashboard helpers."""

from splitmind_ai.ui.dashboard import build_current_dashboard, build_history_rows, build_turn_snapshot


def test_build_turn_snapshot_prefers_surface_signature_over_raw_drive_defaults():
    snapshot = build_turn_snapshot(
        {
            "drive_state": {
                "top_drives": [
                    {"name": "attachment_closeness", "value": 0.7, "target": "user", "frustration": 0.2},
                ]
            },
            "conversation_policy": {"selected_mode": "soften"},
            "trace": {
                "surface_realization": {
                    "latent_drive_signature": {
                        "primary_drive": "attachment_closeness",
                        "secondary_drive": "",
                        "target": "user",
                        "intensity": 0.74,
                        "frustration": 0.45,
                        "carryover": 0.22,
                        "suppression_load": 0.13,
                        "satiation": 0.4,
                        "latent_signal_hint": "guarded warmth",
                    }
                }
            },
        },
        1,
    )

    assert snapshot["drive"]["intensity"] == 0.74
    assert snapshot["drive"]["frustration"] == 0.45
    assert snapshot["drive"]["latent_drive_signature"]["latent_signal_hint"] == "guarded warmth"


def test_build_history_rows_uses_drive_metrics_for_affect_series():
    snapshots = [
        {
            "turn": 1,
            "drive": {
                "intensity": 0.3,
                "frustration": 0.4,
                "carryover": 0.2,
                "suppression_load": 0.6,
                "satiation": 0.1,
            },
            "relationship": {},
            "events": [],
            "timing": {},
        },
        {
            "turn": 2,
            "drive": {
                "intensity": 0.6,
                "frustration": 0.5,
                "carryover": 0.3,
                "suppression_load": 0.2,
                "satiation": 0.4,
            },
            "relationship": {},
            "events": [],
            "timing": {},
        },
    ]

    rows = build_history_rows(snapshots)
    series = [row for row in rows["affect"] if row["metric"] == "suppression_load"]

    assert series == [
        {"turn": 1, "metric": "suppression_load", "value": 0.6},
        {"turn": 2, "metric": "suppression_load", "value": 0.2},
    ]


def test_build_current_dashboard_returns_drive_rows_from_latest_snapshot():
    dashboard = build_current_dashboard([
        {
            "turn": 1,
            "drive": {
                "top_drives": [
                    {"name": "territorial_exclusivity", "value": 0.8, "target": "user"},
                    {"name": "status_recognition", "value": 0.4, "target": "user"},
                ],
                "latent_drive_signature": {"latent_signal_hint": "comparison sting"},
            },
            "policy": {"blocked_by_inhibition": ["full_disclosure"], "satisfaction_goal": "reassert"},
            "relationship": {"unresolved_tensions": []},
            "appraisal": {"dimensions": {}},
            "self_state": {},
            "memory": {"counts": {}, "active_themes": []},
            "events": [],
            "timing": {"nodes": {}},
        }
    ])

    assert dashboard["drive_rows"][0]["label"] == "territorial_exclusivity"
    assert dashboard["current"]["policy"]["satisfaction_goal"] == "reassert"


def test_build_current_dashboard_adds_story_steps_and_residue_rows():
    dashboard = build_current_dashboard([
        {
            "turn": 2,
            "drive": {
                "primary_drive": "territorial_exclusivity",
                "secondary_drive": "status_recognition",
                "top_target": "user",
                "intensity": 0.88,
                "frustration": 0.64,
                "carryover": 0.41,
                "suppression_load": 0.52,
                "satiation": 0.17,
                "latent_drive_signature": {"latent_signal_hint": "comparison sting"},
                "top_drives": [{"name": "territorial_exclusivity", "value": 0.88, "target": "user"}],
            },
            "policy": {
                "selected_mode": "tease",
                "blocked_by_inhibition": ["full_disclosure"],
                "satisfaction_goal": "reassert",
                "candidates": [],
            },
            "supervisor": {"leakage_level": 0.36},
            "relationship": {"unresolved_tensions": []},
            "appraisal": {"dimensions": {}},
            "self_state": {},
            "memory": {"counts": {}, "active_themes": []},
            "events": [],
            "timing": {"nodes": {}},
        }
    ])

    assert dashboard["drive_story"].startswith("territorial_exclusivity is aimed at user")
    assert [step["stage"] for step in dashboard["story_steps"]] == [
        "Drive",
        "Target",
        "Inhibition",
        "Mode",
        "Surface",
    ]
    assert [row["key"] for row in dashboard["residue_rows"]] == [
        "intensity",
        "frustration",
        "carryover",
        "suppression_load",
        "satiation",
    ]


def test_build_current_dashboard_empty_state_includes_visual_defaults():
    dashboard = build_current_dashboard([])

    assert dashboard["drive_story"] == "No active drive loop yet."
    assert dashboard["story_steps"] == []
    assert dashboard["residue_rows"] == []
