from types import SimpleNamespace

import splitmind_ai.ui.app as app_module
from splitmind_ai.ui.app import (
    _assistant_trace_indices,
    _build_turn_state,
    _get_or_create_runtime,
    _init_session_state,
    _reset_session_state,
    _resolve_startup_user_id,
)
from splitmind_ai.ui.dashboard import (
    build_current_dashboard,
    build_history_rows,
    build_turn_snapshot,
)


def test_assistant_trace_indices_align_to_assistant_order():
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
        {"role": "assistant", "content": "a3"},
    ]

    assert _assistant_trace_indices(messages) == [None, 0, None, 1, None, 2]


def test_assistant_trace_indices_ignore_non_assistant_messages():
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "system", "content": "s1"},
        {"role": "assistant", "content": "a1"},
    ]

    assert _assistant_trace_indices(messages) == [None, None, 0]


def test_build_turn_state_carries_forward_agent_state():
    latest_state = {
        "persona": {"persona_name": "warm_guarded_companion"},
        "relationship": {"trust": 0.55, "intimacy": 0.26, "distance": 0.56, "tension": 0.05},
        "mood": {"base_mood": "withdrawn", "turns_since_shift": 0},
        "memory": {"session_summaries": [], "emotional_memories": [], "semantic_preferences": []},
        "drive_state": {"drive_vector": {"attachment_closeness": 0.62}},
        "inhibition_state": {"blocked_modes": ["full_disclosure"]},
        "_internal": {"session": {"session_id": "s1", "user_id": "default"}},
        "conversation": {"summary": "prior summary"},
    }
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "tell me more"},
    ]

    state = _build_turn_state(
        user_message="tell me more",
        session_id="s1",
        user_id="user-42",
        response_language="auto",
        turn_count=1,
        latest_state=latest_state,
        messages=messages,
    )

    assert state["relationship"]["trust"] == 0.55
    assert state["mood"]["base_mood"] == "withdrawn"
    assert state["drive_state"]["drive_vector"]["attachment_closeness"] == 0.62
    assert state["inhibition_state"]["blocked_modes"] == ["full_disclosure"]
    assert state["request"]["user_id"] == "user-42"
    assert state["request"]["response_language"] == "en"
    assert state["_internal"]["session"]["session_id"] == "s1"
    assert state["conversation"]["recent_messages"] == messages
    assert state["conversation"]["summary"] == "prior summary"
    assert "dynamics" not in state


def test_build_turn_state_first_turn_starts_minimal():
    state = _build_turn_state(
        user_message="hello",
        session_id="s1",
        user_id="user-42",
        response_language="ja",
        turn_count=0,
        latest_state={"relationship": {"trust": 0.9}},
        messages=[{"role": "user", "content": "hello"}],
    )

    assert "relationship" not in state
    assert state["request"]["user_id"] == "user-42"
    assert state["request"]["response_language"] == "ja"
    assert state["_internal"]["is_first_turn"] is True


def test_resolve_startup_user_id_prefers_cli_arg():
    user_id = _resolve_startup_user_id(
        argv=["--user-id", "alice"],
        environ={"SPLITMIND_USER_ID": "env-user"},
    )

    assert user_id == "alice"


def test_resolve_startup_user_id_uses_env_and_sanitizes_path_separators():
    user_id = _resolve_startup_user_id(
        argv=[],
        environ={"SPLITMIND_USER_ID": "team/red"},
    )

    assert user_id == "team_red"


def test_init_session_state_sets_startup_user_id_once():
    session_state = {}

    _init_session_state(session_state, startup_user_id="alice")
    _init_session_state(session_state, startup_user_id="bob")

    assert session_state["user_id"] == "alice"
    assert session_state["response_language"] == "auto"


def test_get_or_create_runtime_reuses_compiled_graph_for_same_config(monkeypatch):
    session_state = {}
    settings = SimpleNamespace(
        llm=SimpleNamespace(
            provider="openai",
            model="gpt-test",
            azure_deployment="unused",
            api_version="2024-12-01-preview",
        ),
    )
    llm_calls = []
    graph_calls = []

    def fake_create_chat_llm(resolved_settings):
        llm_calls.append(resolved_settings)
        return "llm"

    def fake_build_splitmind_graph(*, llm, persona_name, vault_path):
        graph_calls.append((llm, persona_name, vault_path))
        return {"compiled_for": persona_name, "vault_path": vault_path}

    monkeypatch.setattr(app_module, "create_chat_llm", fake_create_chat_llm)
    monkeypatch.setattr("splitmind_ai.app.graph.build_splitmind_graph", fake_build_splitmind_graph)

    first = _get_or_create_runtime(
        session_state=session_state,
        settings=settings,
        persona_name="cold_attached_idol",
        vault_path="/tmp/vault",
    )
    second = _get_or_create_runtime(
        session_state=session_state,
        settings=settings,
        persona_name="cold_attached_idol",
        vault_path="/tmp/vault",
    )

    assert first == second
    assert len(llm_calls) == 1
    assert len(graph_calls) == 1


def test_get_or_create_runtime_rebuilds_when_persona_changes(monkeypatch):
    session_state = {}
    settings = SimpleNamespace(
        llm=SimpleNamespace(
            provider="openai",
            model="gpt-test",
            azure_deployment="unused",
            api_version="2024-12-01-preview",
        ),
    )
    graph_calls = []

    monkeypatch.setattr(app_module, "create_chat_llm", lambda resolved_settings: "llm")
    monkeypatch.setattr(
        "splitmind_ai.app.graph.build_splitmind_graph",
        lambda *, llm, persona_name, vault_path: graph_calls.append(persona_name) or persona_name,
    )

    _get_or_create_runtime(
        session_state=session_state,
        settings=settings,
        persona_name="cold_attached_idol",
        vault_path=None,
    )
    _get_or_create_runtime(
        session_state=session_state,
        settings=settings,
        persona_name="warm_guarded_companion",
        vault_path=None,
    )

    assert graph_calls == ["cold_attached_idol", "warm_guarded_companion"]

def test_build_turn_snapshot_extracts_dashboard_metrics():
    result = {
        "relationship": {
            "trust": 0.62,
            "intimacy": 0.4,
            "distance": 0.2,
            "tension": 0.44,
            "attachment_pull": 0.66,
            "unresolved_tensions": [
                {"theme": "fear_of_replacement", "intensity": 0.8, "source": "jealousy"},
                {"theme": "need_for_reassurance", "intensity": 0.4, "source": "repair"},
            ],
        },
        "mood": {
            "base_mood": "defensive",
            "irritation": 0.35,
            "longing": 0.55,
            "protectiveness": 0.22,
            "fatigue": 0.1,
            "openness": 0.48,
        },
        "drive_state": {
            "top_drives": [
                {"name": "territorial_exclusivity", "value": 0.89, "target": "user", "frustration": 0.76, "carryover": 0.62, "suppression_load": 0.51, "satiation": 0.14},
                {"name": "status_recognition", "value": 0.44, "target": "user"},
            ]
        },
        "inhibition_state": {"blocked_drives": ["attachment_closeness"]},
        "appraisal": {
            "dominant_appraisal": "competitive",
            "perceived_acceptance": {"score": 0.12},
            "perceived_rejection": {"score": 0.44},
            "perceived_competition": {"score": 0.91},
            "perceived_distance": {"score": 0.33},
            "ambiguity": {"score": 0.21},
            "face_threat": {"score": 0.87},
            "attachment_activation": {"score": 0.8},
            "repair_opportunity": {"score": 0.15},
        },
        "self_state": {
            "pride_level": 0.78,
            "shame_activation": 0.22,
            "dependency_fear": 0.7,
            "desire_for_closeness": 0.45,
            "urge_to_test_user": 0.83,
        },
        "conversation_policy": {
            "selected_mode": "tease",
            "fallback_mode": "withdraw",
            "max_leakage": 0.4,
            "max_directness": 0.5,
            "blocked_by_inhibition": ["full_disclosure"],
            "satisfaction_goal": "reassert_exclusivity_without_admission",
            "candidates": [
                {"label": "dry_tease", "mode": "tease", "score": 0.84},
                {"label": "status_check", "mode": "probe", "score": 0.72},
            ],
        },
        "utterance_plan": {"leakage_level": 0.37, "containment_success": 0.61},
        "trace": {
            "internal_dynamics": {"internal_dynamics_ms": 11.2},
            "supervisor": {"persona_supervisor_ms": 15.4},
            "surface_realization": {
                "surface_realization_ms": 8.9,
                "latent_drive_signature": {
                    "primary_drive": "territorial_exclusivity",
                    "secondary_drive": "status_recognition",
                    "target": "user",
                    "intensity": 0.89,
                    "frustration": 0.76,
                    "carryover": 0.62,
                    "suppression_load": 0.51,
                    "satiation": 0.14,
                    "latent_signal_hint": "comparison sting",
                },
                "blocked_by_inhibition": ["full_disclosure"],
                "satisfaction_goal": "reassert_exclusivity_without_admission",
            },
            "memory_commit": {"memory_commit_ms": 1.7},
        },
        "_internal": {"event_flags": {"jealousy_trigger": True, "repair_attempt": False}},
        "memory": {"emotional_memories": [1, 2], "semantic_preferences": [1]},
        "working_memory": {"active_themes": ["jealousy", "special_to_user"]},
    }

    snapshot = build_turn_snapshot(result, 3)

    assert snapshot["turn"] == 3
    assert snapshot["relationship"]["trust"] == 0.62
    assert snapshot["drive"]["primary_drive"] == "territorial_exclusivity"
    assert snapshot["drive"]["top_target"] == "user"
    assert snapshot["drive"]["latent_drive_signature"]["latent_signal_hint"] == "comparison sting"
    assert snapshot["appraisal"]["dimensions"]["perceived_competition"] == 0.91
    assert snapshot["self_state"]["urge_to_test_user"] == 0.83
    assert snapshot["policy"]["selected_mode"] == "tease"
    assert snapshot["policy"]["blocked_by_inhibition"] == ["full_disclosure"]
    assert snapshot["policy"]["satisfaction_goal"] == "reassert_exclusivity_without_admission"
    assert snapshot["events"] == ["jealousy_trigger"]
    assert snapshot["memory"]["counts"]["emotional_memories"] == 2
    assert snapshot["memory"]["active_themes"] == ["jealousy", "special_to_user"]
    assert snapshot["timing"]["nodes"]["internal_dynamics"] == 11.2
    assert snapshot["timing"]["total_ms"] == 37.2


def test_build_turn_snapshot_is_missing_safe():
    snapshot = build_turn_snapshot({}, 1)

    assert snapshot["turn"] == 1
    assert snapshot["relationship"]["trust"] == 0.0
    assert snapshot["mood"]["base_mood"] is None
    assert snapshot["drive"]["primary_drive"] == ""
    assert snapshot["events"] == []
    assert snapshot["policy"]["candidates"] == []
    assert snapshot["memory"]["counts"]["active_themes"] == 0


def test_build_history_rows_returns_turn_sorted_series():
    snapshots = [
        build_turn_snapshot(
            {
                "relationship": {"trust": 0.7, "intimacy": 0.2, "distance": 0.4, "tension": 0.2, "attachment_pull": 0.5},
                "drive_state": {
                    "top_drives": [{"name": "attachment_closeness", "value": 0.6, "frustration": 0.2, "carryover": 0.4, "suppression_load": 0.1, "satiation": 0.3}]
                },
                "_internal": {"event_flags": {"repair_attempt": True}},
            },
            2,
        ),
        build_turn_snapshot(
            {
                "relationship": {"trust": 0.5, "intimacy": 0.1, "distance": 0.6, "tension": 0.4, "attachment_pull": 0.3},
                "drive_state": {
                    "top_drives": [{"name": "territorial_exclusivity", "value": 0.3, "frustration": 0.5, "carryover": 0.2, "suppression_load": 0.6, "satiation": 0.1}]
                },
                "_internal": {"event_flags": {"jealousy_trigger": True}},
            },
            1,
        ),
    ]

    rows = build_history_rows(snapshots)

    trust_rows = [row for row in rows["relationship"] if row["metric"] == "trust"]
    affect_rows = [row for row in rows["affect"] if row["metric"] == "frustration"]
    assert [row["turn"] for row in trust_rows] == [1, 2]
    assert [row["value"] for row in affect_rows] == [0.5, 0.2]
    assert rows["events"] == [
        {"turn": 1, "event": "jealousy_trigger", "value": 1.0},
        {"turn": 2, "event": "repair_attempt", "value": 1.0},
    ]


def test_build_current_dashboard_returns_empty_candidate_rows_when_missing():
    dashboard = build_current_dashboard([build_turn_snapshot({}, 1)])

    assert dashboard["turns"] == 1
    assert dashboard["candidate_rows"] == []
    assert dashboard["drive_rows"] == []
    assert dashboard["event_groups"] == []
    assert dashboard["timing_rows"] == []


def test_build_current_dashboard_exposes_drive_rows_and_surface_trace():
    dashboard = build_current_dashboard([
        build_turn_snapshot(
            {
                "drive_state": {
                    "top_drives": [
                        {"name": "territorial_exclusivity", "value": 0.82, "target": "user"},
                        {"name": "status_recognition", "value": 0.48, "target": "user"},
                    ]
                },
                "conversation_policy": {
                    "selected_mode": "tease",
                    "blocked_by_inhibition": ["full_disclosure"],
                    "satisfaction_goal": "reassert_exclusivity_without_admission",
                },
                "trace": {
                    "surface_realization": {
                        "latent_drive_signature": {
                            "primary_drive": "territorial_exclusivity",
                            "target": "user",
                            "intensity": 0.82,
                            "frustration": 0.64,
                            "carryover": 0.41,
                            "suppression_load": 0.33,
                            "satiation": 0.12,
                            "latent_signal_hint": "comparison sting",
                        },
                        "blocked_by_inhibition": ["full_disclosure"],
                        "satisfaction_goal": "reassert_exclusivity_without_admission",
                    }
                },
            },
            1,
        )
    ])

    assert dashboard["drive_rows"][0]["label"] == "territorial_exclusivity"
    assert dashboard["current"]["policy"]["blocked_by_inhibition"] == ["full_disclosure"]
    assert dashboard["current"]["drive"]["latent_drive_signature"]["latent_signal_hint"] == "comparison sting"


def test_build_current_dashboard_clamps_radar_values():
    dashboard = build_current_dashboard([
        build_turn_snapshot(
            {
                "appraisal": {
                    "perceived_acceptance": {"score": 2.0},
                    "perceived_rejection": {"score": -1.0},
                },
                "self_state": {
                    "pride_level": 1.3,
                    "shame_activation": -0.5,
                },
            },
            1,
        )
    ])

    appraisal = {row["axis"]: row["value"] for row in dashboard["appraisal_radar"]}
    self_state = {row["axis"]: row["value"] for row in dashboard["self_state_radar"]}

    assert appraisal["perceived_acceptance"] == 1.0
    assert appraisal["perceived_rejection"] == 0.0
    assert self_state["pride_level"] == 1.0
    assert self_state["shame_activation"] == 0.0


def test_reset_session_state_clears_turn_snapshots():
    session_state = {
        "messages": [{"role": "assistant", "content": "hi"}],
        "session_id": "old",
        "turn_count": 3,
        "traces": [{"trace": 1}],
        "latest_state": {"relationship": {"trust": 0.7}},
        "turn_snapshots": [{"turn": 1}],
    }

    _reset_session_state(session_state)

    assert session_state["messages"] == []
    assert session_state["turn_count"] == 0
    assert session_state["traces"] == []
    assert session_state["latest_state"] == {}
    assert session_state["turn_snapshots"] == []
    assert session_state["session_id"] != "old"
