from splitmind_ai.app.runtime import _build_turn_state


def test_build_turn_state_carries_forward_agent_state():
    latest_state = {
        "persona": {"persona_name": "warm_guarded_companion"},
        "relationship": {"trust": 0.55, "intimacy": 0.26, "distance": 0.56, "tension": 0.05},
        "mood": {"base_mood": "withdrawn", "turns_since_shift": 0},
        "memory": {"session_summaries": [], "emotional_memories": [], "semantic_preferences": []},
        "drive_state": {"drive_vector": {"attachment_closeness": 0.6}},
        "inhibition_state": {"blocked_modes": ["full_disclosure"]},
        "dynamics": {"dominant_desire": "fear_of_rejection", "affective_pressure": 0.7},
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

    assert state["relationship"]["trust"] == 0.55
    assert state["mood"]["base_mood"] == "withdrawn"
    assert state["_internal"]["session"]["session_id"] == "s1"
    assert state["conversation"]["recent_messages"] == messages
    assert state["conversation"]["summary"] == "prior summary"
    assert state["request"]["response_language"] == "en"
    assert state["drive_state"]["drive_vector"]["attachment_closeness"] == 0.6
    assert state["inhibition_state"]["blocked_modes"] == ["full_disclosure"]
    assert "dynamics" not in state


def test_build_turn_state_first_turn_starts_minimal():
    state = _build_turn_state(
        user_message="hello",
        session_id="s1",
        user_id="default",
        response_language="ja",
        turn_count=0,
        latest_state={"relationship": {"trust": 0.9}},
        messages=[{"role": "user", "content": "hello"}],
    )

    assert "relationship" not in state
    assert state["request"]["response_language"] == "ja"
    assert state["_internal"]["is_first_turn"] is True
