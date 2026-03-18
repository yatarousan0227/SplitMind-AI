"""Tests for next-generation state slice definitions."""

from splitmind_ai.state.agent_state import CUSTOM_SLICES, SplitMindAgentState


def test_custom_slices_match_state_keys():
    """All custom slices should correspond to SplitMindAgentState annotations."""
    state_keys = set(SplitMindAgentState.__annotations__.keys())
    for slice_name in CUSTOM_SLICES:
        assert slice_name in state_keys, f"Slice '{slice_name}' not in SplitMindAgentState"


def test_state_can_be_constructed_empty():
    """SplitMindAgentState should be constructable with no fields."""
    state: SplitMindAgentState = {}
    assert isinstance(state, dict)


def test_state_can_hold_new_slices():
    """State should accept the new conflict-engine-oriented slice structure."""
    state: SplitMindAgentState = {
        "request": {"session_id": "test", "user_message": "hello"},
        "response": {},
        "persona": {
            "persona_version": 2,
            "identity": {
                "self_name": "Airi",
                "display_name": "Cold Attached Idol",
            },
            "gender": "female",
            "psychodynamics": {
                "drives": {"closeness": 0.72, "status": 0.81},
                "threat_sensitivity": {"rejection": 0.84},
                "superego_configuration": {"dependency_shame": 0.79},
            },
            "relational_profile": {
                "attachment_pattern": "avoidant_leaning",
                "default_role_frame": "selective_one_to_one",
                "intimacy_regulation": {"preferred_distance": 0.62},
                "trust_dynamics": {"gain_speed": 0.34},
                "dependency_model": {"accepts_user_dependence": 0.61},
                "exclusivity_orientation": {"desires_priority": 0.74},
                "repair_orientation": {"apology_receptivity": 0.22},
            },
            "defense_organization": {
                "primary_defenses": {"ironic_deflection": 0.75},
                "secondary_defenses": {"partial_disclosure": 0.35},
            },
            "ego_organization": {
                "affect_tolerance": 0.43,
                "impulse_regulation": 0.67,
                "ambivalence_capacity": 0.72,
                "mentalization": 0.64,
                "self_observation": 0.59,
                "self_disclosure_tolerance": 0.22,
                "warmth_recovery_speed": 0.37,
            },
            "safety_boundary": {
                "hard_limits": {"max_direct_neediness": 0.18},
            },
        },
        "relationship_state": {
            "durable": {
                "trust": 0.5,
                "intimacy": 0.3,
                "distance": 0.5,
                "attachment_pull": 0.3,
                "relationship_stage": "warming",
                "commitment_readiness": 0.35,
                "repair_depth": 0.1,
            },
            "ephemeral": {
                "tension": 0.22,
                "recent_relational_charge": 0.33,
                "escalation_allowed": False,
                "interaction_fragility": 0.18,
                "turn_local_repair_opening": 0.14,
            },
        },
        "mood": {"base_mood": "calm"},
        "appraisal": {
            "event_type": "repair_offer",
            "valence": "mixed",
            "target_of_tension": "pride",
            "stakes": "high",
            "confidence": 0.84,
            "cues": [{"label": "apology", "evidence": "ごめん", "intensity": 0.7, "confidence": 0.9}],
            "summary_short": "User offers repair.",
            "event_mix": {
                "primary_event": "repair_offer",
                "secondary_events": ["reassurance"],
                "comparison_frame": "none",
                "repair_signal_strength": 0.82,
                "priority_signal_strength": 0.71,
                "distance_signal_strength": 0.0,
            },
            "speaker_intent": {"user_repair_bid": True},
            "perspective_guard": {"preserve_user_as_subject": False},
        },
        "conflict_state": {
            "id_impulse": {
                "dominant_want": "move_closer",
                "secondary_wants": ["stay_safe"],
                "intensity": 0.71,
                "target": "user",
            },
            "superego_pressure": {
                "forbidden_moves": ["direct_neediness"],
                "self_image_to_protect": "composed",
                "pressure": 0.81,
                "shame_load": 0.32,
            },
            "ego_move": {
                "social_move": "accept_but_hold",
                "move_rationale": "Receive but do not collapse distance",
                "dominant_compromise": "take the repair without overexposing",
                "stability": 0.67,
            },
            "residue": {
                "visible_emotion": "pleased_but_guarded",
                "leak_channel": "temperature_gap",
                "residue_text_intent": "let relief leak slightly",
                "intensity": 0.41,
            },
            "expression_envelope": {
                "length": "short",
                "temperature": "cool_warm",
                "directness": 0.31,
                "closure": 0.44,
            },
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
        "working_memory": {
            "active_themes": ["repair"],
            "salient_user_phrases": ["ごめん"],
            "recent_conflict_summaries": [
                {
                    "event_type": "repair_offer",
                    "ego_move": "accept_but_hold",
                    "residue": "pleased_but_guarded",
                    "relationship_delta": "slight trust increase",
                }
            ],
        },
        "memory_interpretation": {
            "event_flags": {"repair_attempt": True},
            "unresolved_tension_summary": ["repair / pride / move_closer"],
            "emotional_memories": [{"event": "ごめん", "emotion": "relief", "intensity": 0.62}],
            "semantic_preferences": [],
            "active_themes": ["repair", "trust"],
            "current_episode_summary": "The user apologized and pushed for repair.",
        },
    }
    assert state["request"]["user_message"] == "hello"
    assert state["relationship_state"]["durable"]["relationship_stage"] == "warming"
    assert state["appraisal"]["event_type"] == "repair_offer"
    assert state["appraisal"]["event_mix"]["secondary_events"] == ["reassurance"]
    assert state["conflict_state"]["ego_move"]["social_move"] == "accept_but_hold"
    assert state["drive_state"]["top_drives"][0]["name"] == "attachment_closeness"
    assert state["working_memory"]["recent_conflict_summaries"][0]["event_type"] == "repair_offer"
    assert state["memory_interpretation"]["event_flags"]["repair_attempt"] is True
