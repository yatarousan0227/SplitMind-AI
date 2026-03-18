from splitmind_ai.app.runtime import _build_turn_state


def test_build_turn_state_carries_forward_agent_state():
    latest_state = {
        "persona": {"persona_version": 2},
        "relationship_state": {
            "durable": {"trust": 0.55, "intimacy": 0.26, "distance": 0.56, "attachment_pull": 0.4},
            "ephemeral": {"tension": 0.05, "recent_relational_charge": 0.12},
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
        user_id="default",
        response_language="auto",
        turn_count=1,
        latest_state=latest_state,
        messages=messages,
    )

    assert state["relationship_state"]["durable"]["trust"] == 0.55
    assert state["mood"]["base_mood"] == "withdrawn"
    assert state["_internal"]["session"]["session_id"] == "s1"
    assert state["conversation"]["recent_messages"] == messages
    assert state["conversation"]["summary"] == "prior summary"
    assert state["request"]["response_language"] == "en"
    assert state["working_memory"]["recent_conflict_summaries"][0]["ego_move"] == "accept_but_hold"
    assert "appraisal" not in state
    assert "conflict_state" not in state


def test_build_turn_state_first_turn_starts_minimal():
    state = _build_turn_state(
        user_message="hello",
        session_id="s1",
        user_id="default",
        response_language="ja",
        turn_count=0,
        latest_state={"relationship_state": {"durable": {"trust": 0.9}}},
        messages=[{"role": "user", "content": "hello"}],
    )

    assert "relationship_state" not in state
    assert state["request"]["response_language"] == "ja"
    assert state["_internal"]["is_first_turn"] is True
