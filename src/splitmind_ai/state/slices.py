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


class PersonaSlice(TypedDict, total=False):
    """Active persona profile loaded from config."""

    persona_version: int
    psychodynamics: PsychodynamicsSlice
    relational_profile: RelationalProfileSlice
    defense_organization: DefenseOrganizationSlice
    ego_organization: EgoOrganizationSlice
    safety_boundary: SafetyBoundarySlice


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

    session_summaries: list[dict]
    emotional_memories: list[dict]
    semantic_preferences: list[dict]


class AppraisalCueSlice(TypedDict, total=False):
    """Compact cue extracted from the user turn."""

    label: str
    evidence: str
    intensity: float
    confidence: float


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

    social_move: str
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
