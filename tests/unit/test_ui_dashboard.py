"""Focused tests for next-generation dashboard helpers."""

from splitmind_ai.ui.dashboard import build_current_dashboard, build_history_rows, build_turn_snapshot


def test_build_turn_snapshot_extracts_relationship_conflict_and_fidelity():
    snapshot = build_turn_snapshot(
        {
            "relationship_state": {
                "durable": {
                    "trust": 0.62,
                    "intimacy": 0.4,
                    "distance": 0.2,
                    "attachment_pull": 0.66,
                    "relationship_stage": "warming",
                    "commitment_readiness": 0.38,
                    "repair_depth": 0.12,
                    "unresolved_tension_summary": ["fear_of_replacement"],
                },
                "ephemeral": {
                    "tension": 0.44,
                    "escalation_allowed": False,
                },
            },
            "mood": {"base_mood": "defensive", "openness": 0.48},
            "appraisal": {
                "event_type": "repair_offer",
                "valence": "mixed",
                "target_of_tension": "pride",
                "stakes": "high",
                "confidence": 0.91,
                "summary_short": "User offers repair with emotional cost.",
                "active_themes": ["repair", "status"],
            },
            "conflict_state": {
                "id_impulse": {"dominant_want": "move_closer", "intensity": 0.74, "target": "user"},
                "superego_pressure": {
                    "forbidden_moves": ["direct_neediness"],
                    "self_image_to_protect": "composed_and_proud",
                    "pressure": 0.81,
                    "shame_load": 0.36,
                },
                "ego_move": {
                    "social_move": "accept_but_hold",
                    "move_rationale": "Receive repair without lowering status",
                    "stability": 0.68,
                },
                "residue": {
                    "visible_emotion": "pleased_but_guarded",
                    "leak_channel": "temperature_gap",
                    "intensity": 0.44,
                },
                "expression_envelope": {
                    "length": "short",
                    "temperature": "cool_warm",
                    "directness": 0.32,
                    "closure": 0.46,
                },
            },
            "trace": {
                "appraisal": {"appraisal_ms": 6.1},
                "conflict_engine": {"conflict_engine_ms": 7.2},
                "expression_realizer": {"expression_realizer_ms": 8.9, "used_llm": True},
                "fidelity_gate": {
                    "fidelity_gate_ms": 1.1,
                    "passed": True,
                    "move_fidelity": 0.82,
                    "residue_fidelity": 0.77,
                    "structural_persona_fidelity": 0.8,
                    "anti_exposition": 0.9,
                    "hard_safety": 1.0,
                    "warnings": [],
                },
                "memory_interpreter": {"memory_interpreter_ms": 2.3, "used_llm": True},
                "memory_commit": {"memory_commit_ms": 1.7},
            },
            "memory": {"emotional_memories": [1, 2], "semantic_preferences": [1]},
            "working_memory": {"active_themes": ["repair", "status"]},
        },
        3,
    )

    assert snapshot["turn"] == 3
    assert snapshot["relationship"]["trust"] == 0.62
    assert snapshot["appraisal"]["event_type"] == "repair_offer"
    assert snapshot["conflict"]["dominant_want"] == "move_closer"
    assert snapshot["expression"]["temperature"] == "cool_warm"
    assert snapshot["fidelity"]["passed"] is True
    assert snapshot["events"] == ["repair_offer"]
    assert snapshot["memory"]["active_themes"] == ["repair", "status"]
    assert snapshot["timing"]["nodes"]["conflict_engine"] == 7.2
    assert snapshot["timing"]["nodes"]["memory_interpreter"] == 2.3
    assert snapshot["timing"]["total_ms"] == 27.3


def test_build_history_rows_uses_conflict_metrics_for_affect_series():
    rows = build_history_rows([
        {
            "turn": 1,
            "relationship": {"trust": 0.4},
            "conflict": {"id_intensity": 0.3, "superego_pressure": 0.4, "residue_intensity": 0.2},
            "expression": {"directness": 0.6, "closure": 0.1},
            "events": [],
            "timing": {},
            "pacing": {"relationship_stage": "unfamiliar"},
        },
        {
            "turn": 2,
            "relationship": {"trust": 0.6},
            "conflict": {"id_intensity": 0.7, "superego_pressure": 0.5, "residue_intensity": 0.4},
            "expression": {"directness": 0.3, "closure": 0.4},
            "events": [],
            "timing": {},
            "pacing": {"relationship_stage": "warming"},
        },
    ])

    series = [row for row in rows["affect"] if row["metric"] == "superego_pressure"]
    assert series == [
        {"turn": 1, "metric": "superego_pressure", "value": 0.4},
        {"turn": 2, "metric": "superego_pressure", "value": 0.5},
    ]
    assert rows["surface"] == [
        {"turn": 1, "metric": "relationship_stage", "value": "unfamiliar"},
        {"turn": 2, "metric": "relationship_stage", "value": "warming"},
    ]


def test_build_current_dashboard_returns_conflict_fidelity_and_expression_rows():
    dashboard = build_current_dashboard([
        build_turn_snapshot(
            {
                "relationship_state": {
                    "durable": {
                        "relationship_stage": "warming",
                        "commitment_readiness": 0.34,
                        "repair_depth": 0.1,
                    },
                    "ephemeral": {"escalation_allowed": False},
                },
                "appraisal": {
                    "event_type": "reassurance",
                    "target_of_tension": "closeness",
                    "stakes": "medium",
                    "confidence": 0.7,
                },
                "conflict_state": {
                    "id_impulse": {"dominant_want": "stay_close", "intensity": 0.82, "target": "user"},
                    "superego_pressure": {"forbidden_moves": ["direct_neediness"], "pressure": 0.64},
                    "ego_move": {"social_move": "allow_dependence_but_reframe", "stability": 0.71},
                    "residue": {"visible_emotion": "warm_but_measured", "intensity": 0.41},
                    "expression_envelope": {"length": "short", "temperature": "warm", "directness": 0.44, "closure": 0.31},
                },
                "trace": {
                    "fidelity_gate": {
                        "passed": True,
                        "move_fidelity": 0.88,
                        "residue_fidelity": 0.75,
                        "structural_persona_fidelity": 0.83,
                        "anti_exposition": 0.91,
                        "hard_safety": 1.0,
                        "warnings": [],
                    }
                },
            },
            1,
        )
    ])

    assert dashboard["conflict_story"].startswith("stay_close is aimed at user")
    assert dashboard["conflict_rows"][0]["label"] == "Dominant want"
    assert dashboard["expression_rows"][0]["value"] == "short"
    assert dashboard["pacing_rows"][0]["value"] == "warming"
    assert dashboard["fidelity_rows"][0]["value"] == "yes"
    assert dashboard["appraisal_radar"][0]["axis"] == "confidence"


def test_build_current_dashboard_empty_state_includes_visual_defaults():
    dashboard = build_current_dashboard([])

    assert dashboard["conflict_story"] == "No active conflict loop yet."
    assert dashboard["story_steps"] == []
    assert dashboard["residue_rows"] == []
    assert dashboard["expression_rows"] == []
    assert dashboard["pacing_rows"] == []
    assert dashboard["fidelity_rows"] == []


def test_build_turn_snapshot_normalizes_theme_objects_and_tension_sources():
    snapshot = build_turn_snapshot(
        {
            "relationship_state": {
                "durable": {
                    "unresolved_tension_summary": [
                        {
                            "theme": "ambiguity",
                            "intensity": 0.72,
                            "source": {
                                "source": "こんにちは、ちょっとお話ししたいんだけど、すこしだけ聞いてくれる？",
                                "created_at": "2026-03-18T16:43:26.429679",
                            },
                        }
                    ]
                }
            },
            "working_memory": {
                "active_themes": [
                    {"theme": "move_closer", "intensity": 0.55},
                    {"source": "user"},
                    "ambiguity",
                ]
            },
        },
        1,
    )

    assert snapshot["relationship"]["unresolved_tensions"] == [
        {
            "theme": "ambiguity",
            "intensity": 0.72,
            "source": "こんにちは、ちょっとお話ししたいんだけど、すこしだけ聞いてくれる？",
        }
    ]
    assert snapshot["memory"]["active_themes"] == ["move_closer", "user", "ambiguity"]
