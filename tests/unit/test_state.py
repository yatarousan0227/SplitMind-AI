"""Tests for state model validation."""

from splitmind_ai.state.agent_state import CUSTOM_SLICES, SplitMindAgentState


def test_custom_slices_match_state_keys():
    """All custom slices should correspond to SplitMindAgentState annotations."""
    state_keys = set(SplitMindAgentState.__annotations__.keys())
    for slice_name in CUSTOM_SLICES:
        assert slice_name in state_keys, f"Slice '{slice_name}' not in SplitMindAgentState"


def test_state_can_be_constructed_empty():
    """SplitMindAgentState should be constructable with no fields (total=False)."""
    state: SplitMindAgentState = {}
    assert isinstance(state, dict)


def test_state_can_hold_slices():
    """State should accept valid slice dicts."""
    state: SplitMindAgentState = {
        "request": {"session_id": "test", "user_message": "hello"},
        "response": {},
        "relationship": {"trust": 0.5, "intimacy": 0.3},
        "mood": {"base_mood": "calm"},
        "appraisal": {
            "dominant_appraisal": "competitive",
            "perceived_competition": {"score": 0.8, "confidence": 0.9},
        },
        "social_model": {
            "user_current_intent_hypotheses": [
                {"label": "share", "confidence": 0.7}
            ],
        },
        "self_state": {
            "pride_level": 0.6,
            "active_defenses": ["ironic_deflection"],
        },
        "drive_state": {
            "drive_vector": {
                "attachment_closeness": 0.8,
                "autonomy_preservation": 0.6,
            },
            "top_drives": [
                {"name": "attachment_closeness", "value": 0.8, "target": "user"},
                {"name": "autonomy_preservation", "value": 0.6},
            ],
            "drive_targets": {"attachment_closeness": "user"},
            "frustration_vector": {"territorial_exclusivity": 0.2},
        },
        "inhibition_state": {
            "role_pressure": 0.4,
            "face_preservation": 0.7,
            "blocked_modes": ["full_disclosure"],
            "preferred_defenses": ["partial_disclosure"],
        },
        "conversation_policy": {
            "selected_mode": "tease",
            "selection_rationale": "Protect face while engaging",
            "competing_drives": ["attachment_closeness", "autonomy_preservation"],
        },
        "utterance_plan": {
            "surface_intent": "test the user lightly",
            "candidates": [
                {"label": "dry_tease", "mode": "tease"},
                {"label": "cool_probe", "mode": "probe"},
            ],
        },
        "working_memory": {
            "active_themes": ["comparison"],
            "salient_user_phrases": ["他の人と楽しかった"],
        },
    }
    assert state["request"]["user_message"] == "hello"
    assert state["relationship"]["trust"] == 0.5
    assert state["appraisal"]["dominant_appraisal"] == "competitive"
    assert state["drive_state"]["top_drives"][0]["name"] == "attachment_closeness"
    assert state["inhibition_state"]["blocked_modes"] == ["full_disclosure"]
    assert state["conversation_policy"]["selected_mode"] == "tease"
    assert state["utterance_plan"]["candidates"][0]["label"] == "dry_tease"
