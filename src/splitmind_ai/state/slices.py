"""State slice definitions for next-generation SplitMind-AI."""

from __future__ import annotations

from typing import Any, TypedDict


class RequestSlice(TypedDict, total=False):
    """Normalized user input for the current turn."""

    session_id: str
    user_id: str
    user_message: str
    response_language: str
    action: str
    params: dict | None
    message: str | None
    turn_number: int


class ResponseSlice(TypedDict, total=False):
    """Final agent output."""

    response_type: str | None
    response_data: dict | None
    response_message: str | None
    final_response_text: str | None


class ConversationSlice(TypedDict, total=False):
    """Recent conversation context."""

    recent_messages: list[dict]
    summary: str | None
    turn_count: int


class PsychodynamicsSlice(TypedDict, total=False):
    """Static motivational and superego priors."""

    drives: dict[str, float]
    threat_sensitivity: dict[str, float]
    superego_configuration: dict[str, float]


class RelationalProfileSlice(TypedDict, total=False):
    """Static priors for how the persona relates to others."""

    attachment_pattern: str
    default_role_frame: str
    intimacy_regulation: dict[str, float]
    trust_dynamics: dict[str, float]
    dependency_model: dict[str, float]
    exclusivity_orientation: dict[str, float]
    repair_orientation: dict[str, float]


class DefenseOrganizationSlice(TypedDict, total=False):
    """Preferred defenses and decompensation tendencies."""

    primary_defenses: dict[str, float]
    secondary_defenses: dict[str, float]


class EgoOrganizationSlice(TypedDict, total=False):
    """Regulatory capacities used by the conflict engine."""

    affect_tolerance: float
    impulse_regulation: float
    ambivalence_capacity: float
    mentalization: float
    self_observation: float
    self_disclosure_tolerance: float
    warmth_recovery_speed: float


class SafetyBoundarySlice(TypedDict, total=False):
    """Hard limits for the persona."""

    hard_limits: dict[str, float]


class RelationalPolicySlice(TypedDict, total=False):
    """Persona-specific relational negotiation policy."""

    repair_style: str
    comparison_style: str
    distance_management_style: str
    status_maintenance_style: str
    warmth_release_style: str
    priority_response_style: str
    residue_persistence: dict[str, float]


class PersonaIdentitySlice(TypedDict, total=False):
    """Identity information carried with the active persona."""

    self_name: str
    display_name: str | None


class PersonaSlice(TypedDict, total=False):
    """Active persona profile loaded from config."""

    persona_version: int
    identity: PersonaIdentitySlice
    gender: str
    psychodynamics: PsychodynamicsSlice
    relational_profile: RelationalProfileSlice
    defense_organization: DefenseOrganizationSlice
    ego_organization: EgoOrganizationSlice
    safety_boundary: SafetyBoundarySlice
    relational_policy: RelationalPolicySlice


class RelationshipDurableStateSlice(TypedDict, total=False):
    """Relationship history that should persist across sessions."""

    trust: float
    intimacy: float
    distance: float
    attachment_pull: float
    relationship_stage: str
    commitment_readiness: float
    repair_depth: float
    unresolved_tension_summary: list[str]


class RelationshipEphemeralStateSlice(TypedDict, total=False):
    """Transient relationship charge that may decay or be recomputed."""

    tension: float
    recent_relational_charge: float
    escalation_allowed: bool
    interaction_fragility: float
    turn_local_repair_opening: float
    repair_mode: str


class RelationshipStateSlice(TypedDict, total=False):
    """Complete relationship state used by the conflict engine."""

    durable: RelationshipDurableStateSlice
    ephemeral: RelationshipEphemeralStateSlice


class MoodSlice(TypedDict, total=False):
    """Short-term agent mood state."""

    base_mood: str
    irritation: float
    longing: float
    protectiveness: float
    fatigue: float
    openness: float
    turns_since_shift: int


class MemorySlice(TypedDict, total=False):
    """Loaded memory context for the current turn."""

    relationship_card: dict
    psychological_card: dict
    episodes: list[dict]
    session_digests: list[dict]
    session_summaries: list[dict]
    emotional_memories: list[dict]
    semantic_preferences: list[dict]


class AppraisalCueSlice(TypedDict, total=False):
    """Compact cue extracted from the user turn."""

    label: str
    evidence: str
    intensity: float
    confidence: float


class EventMixSlice(TypedDict, total=False):
    """Mixed-event parse for ambiguous or blended relational turns."""

    primary_event: str
    secondary_events: list[str]
    comparison_frame: str
    repair_signal_strength: float
    priority_signal_strength: float
    distance_signal_strength: float


class RelationalActProfileSlice(TypedDict, total=False):
    """Continuous relational-act strengths kept alongside event labels."""

    affection: float
    repair_bid: float
    reassurance: float
    commitment: float
    priority_restore: float
    comparison: float
    distancing: float


class SpeakerIntentSlice(TypedDict, total=False):
    """User-side intent anchors for perspective-safe downstream reasoning."""

    user_distance_request: bool
    user_repair_bid: bool
    user_comparison_target: str
    user_commitment_signal: bool
    user_is_describing_own_state: bool


class PerspectiveGuardSlice(TypedDict, total=False):
    """Constraints that preserve who is describing or requesting what."""

    preserve_user_as_subject: bool
    disallow_assistant_self_distancing: bool
    rationale: str


class AppraisalSlice(TypedDict, total=False):
    """Relational interpretation of the latest user turn."""

    event_type: str
    valence: str
    target_of_tension: str
    stakes: str
    confidence: float
    cues: list[AppraisalCueSlice]
    summary_short: str
    user_intent_guess: str
    active_themes: list[str]
    event_mix: EventMixSlice
    relational_act_profile: RelationalActProfileSlice
    speaker_intent: SpeakerIntentSlice
    perspective_guard: PerspectiveGuardSlice


class IdImpulseSlice(TypedDict, total=False):
    """Immediate wants activated by the current user turn."""

    dominant_want: str
    secondary_wants: list[str]
    intensity: float
    target: str


class SuperegoPressureSlice(TypedDict, total=False):
    """Constraints and self-image pressures active on this turn."""

    forbidden_moves: list[str]
    self_image_to_protect: str
    pressure: float
    shame_load: float


class EgoMoveSlice(TypedDict, total=False):
    """Integrated social move selected for this turn."""

    move_family: str
    move_style: str
    move_rationale: str
    dominant_compromise: str
    stability: float


class ResidueSlice(TypedDict, total=False):
    """What leaks through after partial containment."""

    visible_emotion: str
    leak_channel: str
    residue_text_intent: str
    intensity: float


class ExpressionEnvelopeSlice(TypedDict, total=False):
    """Low-dimensional rendering constraints derived from conflict outcome."""

    length: str
    temperature: str
    directness: float
    closure: float


class ConflictStateSlice(TypedDict, total=False):
    """Full conflict-engine output for a single turn."""

    id_impulse: IdImpulseSlice
    superego_pressure: SuperegoPressureSlice
    ego_move: EgoMoveSlice
    residue: ResidueSlice
    expression_envelope: ExpressionEnvelopeSlice


class RepairPolicySlice(TypedDict, total=False):
    """Turn-local repair policy."""

    repair_mode: str
    warmth_ceiling: float
    status_preservation_requirement: float
    required_boundary_marker: bool
    followup_pull_allowed: bool


class ComparisonPolicySlice(TypedDict, total=False):
    """Turn-local comparison policy."""

    comparison_threat_level: float
    self_relevance: float
    status_injury: float
    teasing_allowed: bool
    direct_reclaim_allowed: bool


class RequiredSurfaceMarkersSlice(TypedDict, total=False):
    """Required surface markers for a realized response."""

    acknowledge_bid: bool
    holdback_marker: bool
    boundary_marker: bool
    status_marker: bool
    pace_marker: bool


class ForbiddenCollapsesSlice(TypedDict, total=False):
    """Collapse modes that must not happen for the current turn."""

    gratitude_only: bool
    instant_reciprocity: bool
    generic_reassurance: bool
    generic_agreement: bool
    full_repair_reset: bool


class TurnShapingPolicySlice(TypedDict, total=False):
    """Shared shaping policy bridging appraisal and realization."""

    primary_frame: str
    secondary_frame: str
    preserved_counterforce: str
    warmth_floor: float
    warmth_ceiling: float
    reciprocity_ceiling: float
    disclosure_ceiling: float
    required_surface_markers: RequiredSurfaceMarkersSlice
    forbidden_collapses: ForbiddenCollapsesSlice
    followup_pull_allowed: bool
    surface_guidance_mode: str


class ActiveResidueSlice(TypedDict, total=False):
    """One active short-horizon residue."""

    label: str
    intensity: float
    decay: float
    persona_modifier: float
    linked_theme: str
    source_event: str


class ResidueStateSlice(TypedDict, total=False):
    """Residue carried across turns."""

    active_residues: list[ActiveResidueSlice]
    dominant_residue: str
    overall_load: float
    trigger_links: list[str]


class DriveAxisSlice(TypedDict, total=False):
    """One persistent drive axis and its regulatory metadata."""

    name: str
    value: float
    target: str | None
    urgency: float
    frustration: float
    satiation: float
    carryover: float
    suppression_load: float


class DriveStateSlice(TypedDict, total=False):
    """Persistent motivational state kept across turns."""

    drive_vector: dict[str, float]
    top_drives: list[DriveAxisSlice]
    drive_targets: dict[str, str]
    frustration_vector: dict[str, float]
    satiation_vector: dict[str, float]
    suppression_vector: dict[str, float]
    carryover_vector: dict[str, float]
    last_satisfied_drive: str | None
    last_blocked_drive: str | None
    summary_short: str


class ConflictMemoryEntrySlice(TypedDict, total=False):
    """Compact record of a recent unresolved or notable conflict turn."""

    event_type: str
    ego_move: str
    residue: str
    user_impact: str
    relationship_delta: str


class WorkingMemorySlice(TypedDict, total=False):
    """In-session transient memory used before long-term persistence."""

    active_themes: list[str]
    salient_user_phrases: list[str]
    retrieved_memory_ids: list[str]
    unresolved_questions: list[str]
    current_episode_summary: str | None
    recent_conflict_summaries: list[ConflictMemoryEntrySlice]


class MemoryInterpretationSlice(TypedDict, total=False):
    """LLM-derived persistence interpretation for the completed turn."""

    event_flags: dict[str, bool]
    unresolved_tension_summary: list[str]
    emotional_memories: list[dict]
    semantic_preferences: list[dict]
    active_themes: list[str]
    current_episode_summary: str | None
    recent_conflict_summary: ConflictMemoryEntrySlice | None
    rationale_short: str


class TraceSlice(TypedDict, total=False):
    """Debug and research trace."""

    appraisal: dict[str, Any] | None
    conflict_engine: dict[str, Any] | None
    turn_shaping_policy: dict[str, Any] | None
    repair_policy: dict[str, Any] | None
    comparison_policy: dict[str, Any] | None
    expression_realizer: dict[str, Any] | None
    fidelity_gate: dict[str, Any] | None
    memory_interpreter: dict[str, Any] | None
    memory_commit: dict[str, Any] | None
    error: dict[str, Any] | None


class InternalSlice(TypedDict, total=False):
    """Internal bookkeeping state."""

    active_mode: str | None
    turn_count: int
    is_first_turn: bool
    next_node: str | None
    decision: str | None
    error: str | None
    call_stack: list
    budgets: dict | None
    decision_trace: list
    visited_subgraphs: dict
    step_count: int
    session: dict
    event_flags: dict
    errors: list[dict]
    status: str | None
    persistence: dict | None
