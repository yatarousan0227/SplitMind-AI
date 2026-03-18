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


def test_build_turn_state_carries_forward_new_agent_state():
    latest_state = {
        "persona": {"persona_version": 2},
        "relationship_state": {
            "durable": {"trust": 0.55, "intimacy": 0.26, "distance": 0.56},
            "ephemeral": {"tension": 0.05},
        },
        "mood": {"base_mood": "withdrawn", "turns_since_shift": 0},
        "memory": {"session_summaries": [], "emotional_memories": [], "semantic_preferences": []},
        "working_memory": {"recent_conflict_summaries": [{"turn": 1, "ego_move": "accept_but_hold"}]},
        "appraisal": {"event_type": "repair_offer"},
        "conflict_state": {"ego_move": {"social_move": "accept_but_hold"}},
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

    assert state["relationship_state"]["durable"]["trust"] == 0.55
    assert state["mood"]["base_mood"] == "withdrawn"
    assert state["request"]["user_id"] == "user-42"
    assert state["request"]["response_language"] == "en"
    assert state["_internal"]["session"]["session_id"] == "s1"
    assert state["conversation"]["recent_messages"] == messages
    assert state["conversation"]["summary"] == "prior summary"
    assert "appraisal" not in state
    assert "conflict_state" not in state


def test_build_turn_state_first_turn_starts_minimal():
    state = _build_turn_state(
        user_message="hello",
        session_id="s1",
        user_id="user-42",
        response_language="ja",
        turn_count=0,
        latest_state={"relationship_state": {"durable": {"trust": 0.9}}},
        messages=[{"role": "user", "content": "hello"}],
    )

    assert "relationship_state" not in state
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
    assert session_state["ui_language"] in {"ja", "en"}


def test_get_or_create_runtime_reuses_compiled_graph_for_same_config(monkeypatch):
    session_state = {}
    settings = SimpleNamespace(
        llm=SimpleNamespace(
            provider="openai",
            model="gpt-test",
            azure_deployment="unused",
            api_version="2024-12-01-preview",
        ),
        runtime=SimpleNamespace(max_iterations=16),
    )
    llm_calls = []
    graph_calls = []

    def fake_create_chat_llm(resolved_settings):
        llm_calls.append(resolved_settings)
        return "llm"

    def fake_build_splitmind_graph(*, llm, persona_name, vault_path, max_iterations):
        graph_calls.append((llm, persona_name, vault_path, max_iterations))
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
    assert graph_calls[0][3] == 16


def test_get_or_create_runtime_rebuilds_when_persona_changes(monkeypatch):
    session_state = {}
    settings = SimpleNamespace(
        llm=SimpleNamespace(
            provider="openai",
            model="gpt-test",
            azure_deployment="unused",
            api_version="2024-12-01-preview",
        ),
        runtime=SimpleNamespace(max_iterations=16),
    )
    graph_calls = []

    monkeypatch.setattr(app_module, "create_chat_llm", lambda resolved_settings: "llm")
    monkeypatch.setattr(
        "splitmind_ai.app.graph.build_splitmind_graph",
        (
            lambda *, llm, persona_name, vault_path, max_iterations:
            graph_calls.append((persona_name, max_iterations)) or persona_name
        ),
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

    assert graph_calls == [
        ("cold_attached_idol", 16),
        ("warm_guarded_companion", 16),
    ]


def test_reset_session_state_clears_turn_snapshots():
    session_state = {
        "messages": [{"role": "assistant", "content": "hi"}],
        "session_id": "old",
        "turn_count": 3,
        "traces": [{"trace": 1}],
        "latest_state": {"relationship_state": {"durable": {"trust": 0.7}}},
        "turn_snapshots": [{"turn": 1}],
    }

    _reset_session_state(session_state)

    assert session_state["messages"] == []
    assert session_state["turn_count"] == 0
    assert session_state["traces"] == []
    assert session_state["latest_state"] == {}
    assert session_state["turn_snapshots"] == []
    assert session_state["session_id"] != "old"
