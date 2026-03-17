"""Tests for contract schema validation."""

import pytest
from pydantic import ValidationError

from splitmind_ai.contracts.action_policy import ConversationPolicy
from splitmind_ai.contracts.appraisal import AppraisalBundle, AppraisalLabel
from splitmind_ai.contracts.drive import DriveState, InhibitionState, MotivationalUpdate
from splitmind_ai.contracts.dynamics import (
    DefenseOutput,
    DesireCandidate,
    EgoOutput,
    EventFlags,
    IdOutput,
    InternalDynamicsBundle,
    SuperegoOutput,
)
from splitmind_ai.contracts.memory import (
    EmotionalMemory,
    SemanticPreference,
    SessionSummary,
    UnresolvedTension,
)
from splitmind_ai.contracts.persona import (
    ExpressionSettings,
    PersonaSupervisorFrame,
    UtterancePlan,
)


class TestInternalDynamicsBundle:
    def test_valid_bundle(self):
        bundle = InternalDynamicsBundle.model_validate({
            "id_output": {
                "raw_desire_candidates": [
                    {
                        "desire_type": "jealousy",
                        "intensity": 0.72,
                        "target": "user attention",
                        "direction": "control",
                        "rationale": "user praised third party",
                    }
                ],
                "drive_axes": [
                    {
                        "name": "territorial_exclusivity",
                        "value": 0.74,
                        "target": "user",
                        "urgency": 0.68,
                        "frustration": 0.35,
                        "suppression_load": 0.42,
                    }
                ],
                "affective_pressure_score": 0.65,
                "approach_avoidance_balance": 0.44,
                "target_lock": 0.81,
                "suppression_risk": 0.52,
                "impulse_summary": "Jealousy driven impulse",
            },
            "ego_output": {
                "response_strategy": "ironic_deflection",
                "risk_assessment": "medium",
                "concealment_or_reveal_plan": "conceal jealousy, show mild competition",
            },
            "superego_output": {
                "role_alignment_score": 0.8,
                "ideal_self_gap": 0.3,
                "shame_or_guilt_pressure": 0.4,
            },
            "defense_output": {
                "selected_mechanism": "ironic_deflection",
                "transformation_note": "Redirect jealousy into competitive humor",
                "leakage_recommendation": 0.4,
            },
            "dominant_desire": "jealousy",
            "event_flags": {"jealousy_trigger": True},
        })
        assert bundle.dominant_desire == "jealousy"
        assert bundle.id_output.raw_desire_candidates[0].intensity == 0.72
        assert bundle.id_output.drive_axes[0].name == "territorial_exclusivity"
        assert bundle.event_flags.jealousy_trigger is True

    def test_event_flags_default_to_false(self):
        flags = EventFlags.model_validate({})

        assert flags.reassurance_received is False
        assert flags.jealousy_trigger is False
        assert flags.repair_attempt is False

    def test_intensity_bounds(self):
        with pytest.raises(ValidationError):
            DesireCandidate(
                desire_type="test",
                intensity=1.5,  # Out of bounds
                target="test",
                direction="approach",
                rationale="test",
            )

    def test_id_output_requires_at_least_one_desire(self):
        with pytest.raises(ValidationError):
            IdOutput(
                raw_desire_candidates=[],  # min_length=1
                drive_axes=[{"name": "attachment_closeness", "value": 0.6}],
                affective_pressure_score=0.5,
                approach_avoidance_balance=0.6,
                target_lock=0.4,
                suppression_risk=0.3,
                impulse_summary="test",
            )


class TestPersonaSupervisorPlan:
    def test_valid_frame(self):
        frame = PersonaSupervisorFrame.model_validate({
            "surface_intent": "Acknowledge the user's experience",
            "hidden_pressure": "Mild jealousy",
            "defense_applied": "ironic_deflection",
            "mask_goal": "Look unaffected and a little proud",
            "expression_settings": {
                "length": "short",
                "temperature": "cool",
                "directness": 0.3,
                "ambiguity": 0.5,
                "sharpness": 0.4,
                "hesitation": 0.3,
                "unevenness": 0.4,
            },
            "containment_success": 0.45,
            "rupture_points": ["briefly turns cold", "does not fully say what hurts"],
            "integration_rationale": "Balance pride with engagement",
            "selection_criteria": ["prefer clipped opening", "avoid confession"],
        })
        assert frame.expression_settings.temperature == "cool"
        assert frame.mask_goal == "Look unaffected and a little proud"
        assert frame.containment_success == 0.45
        assert len(frame.selection_criteria) == 2

    def test_utterance_plan_requires_multiple_candidates(self):
        with pytest.raises(ValidationError):
            UtterancePlan.model_validate({
                "frame": {
                    "surface_intent": "test",
                    "hidden_pressure": "test",
                    "defense_applied": "suppression",
                    "expression_settings": {
                        "length": "short",
                        "temperature": "cool",
                        "directness": 0.3,
                        "ambiguity": 0.4,
                        "sharpness": 0.2,
                    },
                    "integration_rationale": "test",
                },
                "candidates": [
                    {
                        "label": "only",
                        "mode": "deflect",
                        "opening_style": "short",
                        "interpersonal_move": "hold",
                        "latent_signal": "hesitation",
                    }
                ],
            })


class TestPhase6Contracts:
    def test_appraisal_bundle_accepts_minimal_strict_payload(self):
        bundle = AppraisalBundle.model_validate({
            "social_cues": [
                {
                    "cue_type": "competition",
                    "evidence": "他の人",
                    "intensity": 0.8,
                    "confidence": 0.9,
                }
            ],
            "appraisal": {
                "perceived_acceptance": {"score": 0.1, "confidence": 0.7},
                "perceived_rejection": {"score": 0.4, "confidence": 0.8},
                "perceived_competition": {"score": 0.9, "confidence": 0.9},
                "perceived_distance": {"score": 0.3, "confidence": 0.7},
                "ambiguity": {"score": 0.2, "confidence": 0.7},
                "face_threat": {"score": 0.6, "confidence": 0.8},
                "attachment_activation": {"score": 0.8, "confidence": 0.9},
                "repair_opportunity": {"score": 0.1, "confidence": 0.6},
                "dominant_appraisal": "competitive",
                "dominant_appraisal_confidence": 0.88,
                "active_wounds": ["fear_of_replacement"],
                "triggered_drives": ["territorial_exclusivity", "threat_avoidance"],
                "self_image_threats": ["special_to_user"],
            },
        })

        assert bundle.appraisal.dominant_appraisal == AppraisalLabel.competitive
        assert bundle.appraisal.summary_short == ""

    def test_appraisal_bundle_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            AppraisalBundle.model_validate({
                "social_cues": [],
                "appraisal": {
                    "perceived_acceptance": {"score": 0.1, "confidence": 0.7},
                    "perceived_rejection": {"score": 0.4, "confidence": 0.8},
                    "perceived_competition": {"score": 0.9, "confidence": 0.9},
                    "perceived_distance": {"score": 0.3, "confidence": 0.7},
                    "ambiguity": {"score": 0.2, "confidence": 0.7},
                    "face_threat": {"score": 0.6, "confidence": 0.8},
                    "attachment_activation": {"score": 0.8, "confidence": 0.9},
                    "repair_opportunity": {"score": 0.1, "confidence": 0.6},
                    "unknown_field": True,
                },
            })

    def test_conversation_policy_accepts_minimal_strict_payload(self):
        policy = ConversationPolicy.model_validate({
            "selected_mode": "tease",
            "candidates": [
                {
                    "mode": "tease",
                    "label": "dry_tease",
                    "score": 0.81,
                    "supporting_appraisals": ["competitive", "threatened"],
                }
            ],
            "selection_rationale": "Teasing preserves face.",
            "drive_rationale": ["territorial_exclusivity remains elevated"],
            "competing_drives": ["territorial_exclusivity", "autonomy_preservation"],
            "blocked_by_inhibition": ["full_disclosure"],
            "satisfaction_goal": "reassert significance",
        })

        assert policy.selected_mode.value == "tease"
        assert policy.candidates[0].supporting_appraisals == ["competitive", "threatened"]
        assert policy.competing_drives == ["territorial_exclusivity", "autonomy_preservation"]
        assert policy.emotion_surface_mode == "indirect_masked"
        assert policy.indirection_strategy == "action_substitution"

    def test_conversation_policy_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            ConversationPolicy.model_validate({
                "selected_mode": "withdraw",
                "selection_rationale": "Pull back",
                "made_up": "nope",
            })


class TestDriveContracts:
    def test_drive_state_validates(self):
        drive_state = DriveState.model_validate({
            "drive_vector": {
                "attachment_closeness": 0.81,
                "autonomy_preservation": 0.62,
            },
            "top_drives": [
                {
                    "name": "attachment_closeness",
                    "value": 0.81,
                    "target": "user",
                    "urgency": 0.73,
                    "carryover": 0.28,
                },
                {
                    "name": "autonomy_preservation",
                    "value": 0.62,
                    "suppression_load": 0.36,
                },
            ],
            "drive_targets": {
                "attachment_closeness": "user",
            },
            "frustration_vector": {
                "territorial_exclusivity": 0.34,
            },
            "carryover_vector": {
                "territorial_exclusivity": 0.22,
            },
            "last_blocked_drive": "attachment_closeness",
        })
        assert drive_state.top_drives[0].target == "user"
        assert drive_state.last_blocked_drive == "attachment_closeness"

    def test_inhibition_state_validates(self):
        inhibition = InhibitionState.model_validate({
            "role_pressure": 0.41,
            "face_preservation": 0.58,
            "dependency_fear": 0.47,
            "pride_level": 0.66,
            "allowed_modes": ["probe", "tease"],
            "blocked_modes": ["full_disclosure"],
            "preferred_defenses": ["ironic_deflection", "partial_disclosure"],
        })
        assert inhibition.blocked_modes == ["full_disclosure"]
        assert inhibition.pride_level == 0.66

    def test_motivational_update_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            MotivationalUpdate.model_validate({
                "changed_drives": ["attachment_closeness"],
                "unexpected": True,
            })


class TestMemorySchemas:
    def test_unresolved_tension(self):
        t = UnresolvedTension(
            theme="fear_of_replacement",
            intensity=0.66,
            source="user praised third party",
        )
        assert t.theme == "fear_of_replacement"
        assert 0 <= t.intensity <= 1

    def test_session_summary(self):
        s = SessionSummary(
            session_id="s1",
            summary="Brief chat",
            turn_count=3,
            dominant_mood="calm",
        )
        assert s.turn_count == 3

    def test_emotional_memory(self):
        em = EmotionalMemory(
            event="User expressed gratitude",
            emotion="warmth",
            intensity=0.7,
        )
        assert em.emotion == "warmth"

    def test_semantic_preference(self):
        sp = SemanticPreference(
            topic="music",
            preference="likes jazz",
        )
        assert sp.confidence == 0.5  # default
