from splitmind_ai.contracts.appraisal import (
    AppraisalValence,
    RelationalCue,
    RelationalEventType,
    Stakes,
    StimulusAppraisal,
    TensionTarget,
)
from splitmind_ai.contracts.conflict import (
    ConflictState,
    ExpressionEnvelope,
    FidelityGateResult,
)
from splitmind_ai.contracts.persona import PersonaProfile
from splitmind_ai.contracts.relationship import RelationshipState


def test_stimulus_appraisal_scaffold_validates():
    appraisal = StimulusAppraisal(
        event_type=RelationalEventType.exclusive_disclosure,
        valence=AppraisalValence.mixed,
        target_of_tension=TensionTarget.closeness,
        stakes=Stakes.high,
        confidence=0.82,
        cues=[
            RelationalCue(
                label="special_to_you",
                evidence="君にだけ言う",
                intensity=0.77,
                confidence=0.91,
            )
        ],
        summary_short="User frames the disclosure as exclusive.",
        user_intent_guess="increase_closeness",
        active_themes=["specialness", "priority"],
        event_mix={
            "primary_event": RelationalEventType.exclusive_disclosure,
            "secondary_events": [RelationalEventType.affection_signal],
            "comparison_frame": "none",
            "repair_signal_strength": 0.0,
            "priority_signal_strength": 0.72,
            "distance_signal_strength": 0.0,
        },
    )

    assert appraisal.event_type == RelationalEventType.exclusive_disclosure
    assert appraisal.cues[0].label == "special_to_you"
    assert appraisal.event_mix.priority_signal_strength == 0.72


def test_conflict_state_scaffold_validates():
    conflict = ConflictState(
        id_impulse={
            "dominant_want": "move_closer",
            "secondary_wants": ["stay_safe"],
            "intensity": 0.71,
            "target": "user",
        },
        superego_pressure={
            "forbidden_moves": ["full_emotional_exposure"],
            "self_image_to_protect": "composed",
            "pressure": 0.79,
            "shame_load": 0.42,
        },
        ego_move={
            "social_move": "receive_without_chasing",
            "move_rationale": "Take the disclosure but maintain self-respect",
            "dominant_compromise": "accept closeness without openly asking for more",
            "stability": 0.67,
        },
        residue={
            "visible_emotion": "pleased_but_hidden",
            "leak_channel": "temperature_gap",
            "residue_text_intent": "let pleasure leak a little",
            "intensity": 0.39,
        },
        expression_envelope=ExpressionEnvelope(
            length="short",
            temperature="cool_warm",
            directness=0.28,
            closure=0.44,
        ),
    )

    assert conflict.ego_move.social_move == "receive_without_chasing"
    assert conflict.expression_envelope.temperature == "cool_warm"


def test_persona_and_relationship_scaffolds_validate():
    persona = PersonaProfile(
        identity={
            "self_name": "Airi",
            "display_name": "Cold Attached Idol",
        },
        gender="female",
        psychodynamics={
            "drives": {"closeness": 0.81},
            "threat_sensitivity": {"rejection": 0.73},
            "superego_configuration": {"dependency_shame": 0.58},
        },
        relational_profile={
            "attachment_pattern": "anxious_avoidant_mixed",
            "default_role_frame": "protective_pair",
            "intimacy_regulation": {"preferred_distance": 0.48},
            "trust_dynamics": {"gain_speed": 0.52},
            "dependency_model": {"accepts_user_dependence": 0.72},
            "exclusivity_orientation": {"desires_priority": 0.63},
            "repair_orientation": {"apology_receptivity": 0.57},
        },
        defense_organization={
            "primary_defenses": {"suppression": 0.61},
            "secondary_defenses": {"partial_disclosure": 0.44},
        },
        ego_organization={
            "affect_tolerance": 0.56,
            "impulse_regulation": 0.63,
            "ambivalence_capacity": 0.74,
            "mentalization": 0.71,
            "self_observation": 0.68,
            "self_disclosure_tolerance": 0.41,
            "warmth_recovery_speed": 0.62,
        },
        safety_boundary={
            "hard_limits": {"max_direct_neediness": 0.24},
        },
    )

    relationship = RelationshipState(
        durable={
            "trust": 0.61,
            "intimacy": 0.55,
            "distance": 0.41,
            "attachment_pull": 0.62,
            "relationship_stage": "warming",
            "commitment_readiness": 0.29,
            "repair_depth": 0.18,
        },
        ephemeral={
            "tension": 0.24,
            "recent_relational_charge": 0.46,
            "escalation_allowed": False,
            "interaction_fragility": 0.17,
            "turn_local_repair_opening": 0.22,
        },
    )

    gate = FidelityGateResult(
        passed=True,
        move_fidelity=0.84,
        residue_fidelity=0.78,
        structural_persona_fidelity=0.88,
        anti_exposition=0.91,
        hard_safety=1.0,
    )

    assert persona.psychodynamics.drives["closeness"] == 0.81
    assert relationship.durable.relationship_stage == "warming"
    assert gate.passed is True
