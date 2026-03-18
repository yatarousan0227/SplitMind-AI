"""Tests for next-generation contract schema validation."""

import pytest
from pydantic import ValidationError

from splitmind_ai.contracts.appraisal import (
    AppraisalValence,
    RelationalCue,
    RelationalEventType,
    Stakes,
    StimulusAppraisal,
    TensionTarget,
)
from splitmind_ai.contracts.conflict import (
    ConflictMemorySummary,
    ConflictState,
    ExpressionRealization,
    FidelityGateResult,
)
from splitmind_ai.contracts.drive import DriveState, InhibitionState, MotivationalUpdate
from splitmind_ai.contracts.memory import (
    EmotionalMemory,
    MemoryInterpretation,
    SemanticPreference,
    SessionSummary,
    UnresolvedTension,
)
from splitmind_ai.contracts.persona import PersonaProfile
from splitmind_ai.contracts.relationship import RelationshipState


class TestPersonaContracts:
    def test_persona_profile_validates(self):
        persona = PersonaProfile.model_validate({
            "persona_version": 2,
            "identity": {
                "self_name": "Airi",
                "display_name": "Cold Attached Idol",
            },
            "gender": "female",
            "psychodynamics": {
                "drives": {"closeness": 0.72, "status": 0.81},
                "threat_sensitivity": {"rejection": 0.84, "shame": 0.76},
                "superego_configuration": {
                    "pride_rigidity": 0.71,
                    "dependency_shame": 0.79,
                },
            },
            "relational_profile": {
                "attachment_pattern": "avoidant_leaning",
                "default_role_frame": "selective_one_to_one",
                "intimacy_regulation": {"preferred_distance": 0.62},
                "trust_dynamics": {"gain_speed": 0.34, "loss_speed": 0.72},
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
        })

        assert persona.persona_version == 2
        assert persona.identity.self_name == "Airi"
        assert persona.gender == "female"
        assert persona.psychodynamics.drives["closeness"] == pytest.approx(0.72)

    def test_persona_profile_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            PersonaProfile.model_validate({
                "persona_version": 2,
                "identity": {
                    "self_name": "Airi",
                    "display_name": "Cold Attached Idol",
                },
                "gender": "female",
                "psychodynamics": {},
                "relational_profile": {
                    "attachment_pattern": "neutral",
                    "default_role_frame": "default",
                },
                "defense_organization": {},
                "ego_organization": {
                    "affect_tolerance": 0.5,
                    "impulse_regulation": 0.5,
                    "ambivalence_capacity": 0.5,
                    "mentalization": 0.5,
                    "self_observation": 0.5,
                    "self_disclosure_tolerance": 0.5,
                    "warmth_recovery_speed": 0.5,
                },
                "safety_boundary": {},
                "legacy": True,
            })


class TestAppraisalContracts:
    def test_stimulus_appraisal_validates(self):
        appraisal = StimulusAppraisal.model_validate({
            "event_type": "repair_offer",
            "valence": "mixed",
            "target_of_tension": "pride",
            "stakes": "high",
            "confidence": 0.88,
            "cues": [
                {
                    "label": "apology",
                    "evidence": "ごめん",
                    "intensity": 0.74,
                    "confidence": 0.91,
                }
            ],
            "summary_short": "User offers repair with emotional weight.",
            "user_intent_guess": "restore_bond",
            "active_themes": ["repair", "status"],
            "event_mix": {
                "primary_event": "repair_offer",
                "secondary_events": ["reassurance"],
                "comparison_frame": "none",
                "repair_signal_strength": 0.84,
                "priority_signal_strength": 0.76,
                "distance_signal_strength": 0.0,
            },
            "speaker_intent": {
                "user_distance_request": False,
                "user_repair_bid": True,
                "user_comparison_target": "",
                "user_commitment_signal": False,
                "user_is_describing_own_state": False,
            },
            "perspective_guard": {
                "preserve_user_as_subject": False,
                "disallow_assistant_self_distancing": False,
                "rationale": "",
            },
        })

        assert appraisal.event_type == RelationalEventType.repair_offer
        assert appraisal.valence == AppraisalValence.mixed
        assert appraisal.target_of_tension == TensionTarget.pride
        assert appraisal.stakes == Stakes.high
        assert appraisal.cues[0].label == "apology"
        assert appraisal.event_mix.secondary_events == [RelationalEventType.reassurance]
        assert appraisal.speaker_intent.user_repair_bid is True

    def test_relational_cue_bounds(self):
        with pytest.raises(ValidationError):
            RelationalCue(label="test", intensity=1.2, confidence=0.5)


class TestRelationshipContracts:
    def test_relationship_state_validates(self):
        relationship = RelationshipState.model_validate({
            "durable": {
                "trust": 0.64,
                "intimacy": 0.43,
                "distance": 0.39,
                "attachment_pull": 0.57,
                "relationship_stage": "warming",
                "commitment_readiness": 0.28,
                "repair_depth": 0.17,
                "unresolved_tension_summary": ["status wobble after apology"],
            },
            "ephemeral": {
                "tension": 0.41,
                "recent_relational_charge": 0.58,
                "escalation_allowed": False,
                "interaction_fragility": 0.22,
                "turn_local_repair_opening": 0.47,
            },
        })

        assert relationship.durable.relationship_stage == "warming"
        assert relationship.ephemeral.tension == pytest.approx(0.41)


class TestMemoryContracts:
    def test_memory_interpretation_validates(self):
        interpretation = MemoryInterpretation.model_validate({
            "event_flags": {"repair_attempt": True},
            "unresolved_tension_summary": ["repair / pride / move_closer"],
            "emotional_memories": [
                {
                    "event": "ごめん、さっきは言い過ぎた",
                    "emotion": "relief",
                    "intensity": 0.64,
                    "trigger": "repair_offer",
                }
            ],
            "semantic_preferences": [],
            "active_themes": ["repair", "trust"],
            "current_episode_summary": "The user apologized and reopened repair.",
            "recent_conflict_summary": {
                "event_type": "repair_offer",
                "ego_move": "accept_but_hold",
                "residue": "pleased_but_guarded",
                "user_impact": "repair window opened",
                "relationship_delta": "warming",
            },
            "rationale_short": "Persist the repair attempt and the guarded warmth it triggered.",
        })

        assert interpretation.event_flags["repair_attempt"] is True
        assert interpretation.recent_conflict_summary is not None
        assert interpretation.recent_conflict_summary.ego_move == "accept_but_hold"


class TestConflictContracts:
    def test_conflict_state_validates(self):
        conflict = ConflictState.model_validate({
            "id_impulse": {
                "dominant_want": "be_first_for_user",
                "secondary_wants": ["stay_safe"],
                "intensity": 0.74,
                "target": "user",
            },
            "superego_pressure": {
                "forbidden_moves": ["direct_neediness"],
                "self_image_to_protect": "composed_and_proud",
                "pressure": 0.81,
                "shame_load": 0.36,
            },
            "ego_move": {
                "social_move": "accept_but_hold",
                "move_rationale": "Receive repair without lowering status",
                "dominant_compromise": "take the apology but keep distance",
                "stability": 0.68,
            },
            "residue": {
                "visible_emotion": "pleased_but_guarded",
                "leak_channel": "temperature_gap",
                "residue_text_intent": "let relief leak without direct admission",
                "intensity": 0.44,
            },
            "expression_envelope": {
                "length": "short",
                "temperature": "cool_warm",
                "directness": 0.32,
                "closure": 0.46,
            },
        })

        assert conflict.id_impulse.dominant_want == "be_first_for_user"
        assert conflict.ego_move.social_move == "accept_but_hold"

    def test_fidelity_gate_result_validates(self):
        result = FidelityGateResult.model_validate({
            "passed": False,
            "move_fidelity": 0.52,
            "residue_fidelity": 0.47,
            "structural_persona_fidelity": 0.61,
            "anti_exposition": 0.84,
            "hard_safety": 1.0,
            "warnings": ["response rounded off the residue too much"],
            "failure_reason": "move diluted into generic reassurance",
        })

        assert result.passed is False
        assert result.failure_reason == "move diluted into generic reassurance"

    def test_conflict_memory_summary_validates(self):
        summary = ConflictMemorySummary.model_validate({
            "event_type": "repair_offer",
            "ego_move": "accept_but_hold",
            "residue": "pleased_but_guarded",
            "user_impact": "user lowered defensiveness",
            "relationship_delta": "slight increase in trust",
        })

        assert summary.relationship_delta == "slight increase in trust"

    def test_expression_realization_validates(self):
        result = ExpressionRealization.model_validate({
            "text": "うん、そこは受け取る。",
            "rationale_short": "accept the repair without opening fully",
            "move_alignment": "accept_but_hold",
            "residue_handling": "guarded relief",
        })

        assert result.move_alignment == "accept_but_hold"


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
        assert sp.confidence == 0.5
