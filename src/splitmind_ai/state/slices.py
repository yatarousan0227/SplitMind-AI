"""State slice definitions for SplitMind-AI.

All slices are TypedDict for agent-contracts / LangGraph compatibility.
Pydantic models are used separately for contract output schemas.
"""

from __future__ import annotations

from typing import TypedDict


# ---------------------------------------------------------------------------
# request slice
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# response slice
# ---------------------------------------------------------------------------
class ResponseSlice(TypedDict, total=False):
    """Final agent output."""

    response_type: str | None
    response_data: dict | None
    response_message: str | None
    final_response_text: str | None


# ---------------------------------------------------------------------------
# conversation slice
# ---------------------------------------------------------------------------
class ConversationSlice(TypedDict, total=False):
    """Recent conversation context."""

    recent_messages: list[dict]
    summary: str | None
    turn_count: int


# ---------------------------------------------------------------------------
# persona slice
# ---------------------------------------------------------------------------
class PersonaSlice(TypedDict, total=False):
    """Active persona profile loaded from config."""

    persona_name: str
    weights: dict[str, float]
    base_attributes: dict[str, str]
    defense_biases: dict[str, float]
    leakage_policy: dict[str, float]
    tone_guardrails: list[str]
    prohibited_expressions: list[str]


# ---------------------------------------------------------------------------
# relationship slice
# ---------------------------------------------------------------------------
class RelationshipSlice(TypedDict, total=False):
    """Relationship state between agent and user."""

    trust: float
    intimacy: float
    distance: float
    tension: float
    attachment_pull: float
    unresolved_tensions: list[dict]
    user_sensitivities: list[str]
    attachment_tendency: str


# ---------------------------------------------------------------------------
# mood slice
# ---------------------------------------------------------------------------
class MoodSlice(TypedDict, total=False):
    """Short-term agent mood state."""

    base_mood: str  # calm | irritated | longing | defensive | playful | withdrawn
    irritation: float
    longing: float
    protectiveness: float
    fatigue: float
    openness: float
    turns_since_shift: int


# ---------------------------------------------------------------------------
# memory slice
# ---------------------------------------------------------------------------
class MemorySlice(TypedDict, total=False):
    """Loaded memory context for the current turn."""

    session_summaries: list[dict]
    emotional_memories: list[dict]
    semantic_preferences: list[dict]


# ---------------------------------------------------------------------------
# appraisal-oriented slices (phase 6 prep)
# ---------------------------------------------------------------------------
class SocialCueSlice(TypedDict, total=False):
    """Single cue detected from the latest user behavior."""

    cue_type: str
    evidence: str
    intensity: float
    confidence: float


class AppraisalDimensionSlice(TypedDict, total=False):
    """Scalar appraisal dimension with lightweight metadata."""

    score: float
    confidence: float
    rationale_short: str
    trend: str
    driver_cues: list[str]


class AppraisalSlice(TypedDict, total=False):
    """Subjective meaning assigned to the current turn."""

    social_cues: list[SocialCueSlice]
    perceived_acceptance: AppraisalDimensionSlice
    perceived_rejection: AppraisalDimensionSlice
    perceived_competition: AppraisalDimensionSlice
    perceived_distance: AppraisalDimensionSlice
    ambiguity: AppraisalDimensionSlice
    face_threat: AppraisalDimensionSlice
    attachment_activation: AppraisalDimensionSlice
    repair_opportunity: AppraisalDimensionSlice
    dominant_appraisal: str | None
    dominant_appraisal_confidence: float
    active_wounds: list[str]
    summary_short: str


class SocialIntentHypothesisSlice(TypedDict, total=False):
    """Current guess about what the user is trying to do socially."""

    label: str
    confidence: float
    supporting_cues: list[str]


class SocialModelSlice(TypedDict, total=False):
    """Working model of the user carried across turns."""

    user_current_intent_hypotheses: list[SocialIntentHypothesisSlice]
    user_attachment_guess: str
    user_sensitivity_guess: list[str]
    confidence: float
    recent_prediction_errors: list[str]
    last_user_action: str


class SelfStateSlice(TypedDict, total=False):
    """Internal self-protective state for the persona."""

    threatened_self_image: list[str]
    pride_level: float
    shame_activation: float
    dependency_fear: float
    desire_for_closeness: float
    urge_to_test_user: float
    active_defenses: list[str]


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
    """Persistent motivational state used as source of truth."""

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


class InhibitionStateSlice(TypedDict, total=False):
    """Self-protective constraints that block or permit action modes."""

    role_pressure: float
    face_preservation: float
    dependency_fear: float
    pride_level: float
    allowed_modes: list[str]
    blocked_modes: list[str]
    preferred_defenses: list[str]
    blocked_drives: list[str]


class ActionCandidateSlice(TypedDict, total=False):
    """One social action option under consideration."""

    mode: str
    label: str
    score: float
    rationale_short: str
    risk_level: float
    defense_hint: str
    supporting_appraisals: list[str]
    estimated_user_impact: str


class ConversationPolicySlice(TypedDict, total=False):
    """Selected action policy for the current turn."""

    selected_mode: str
    candidates: list[ActionCandidateSlice]
    selection_rationale: str
    fallback_mode: str
    target_user_effect: str
    drive_rationale: list[str]
    competing_drives: list[str]
    blocked_by_inhibition: list[str]
    satisfaction_goal: str
    max_leakage: float
    max_directness: float
    blocked_modes: list[str]


class UtteranceBlueprintSlice(TypedDict, total=False):
    """A single plausible utterance direction before surface text is finalized."""

    label: str
    mode: str
    opening_style: str
    interpersonal_move: str
    latent_signal: str
    must_include: list[str]
    avoid: list[str]


class UtterancePlanSlice(TypedDict, total=False):
    """Intermediate plan for candidate-based utterance generation."""

    surface_intent: str
    hidden_pressure: str
    defense_applied: str
    mask_goal: str
    expression_settings: dict
    tone_profile: dict
    leakage_level: float
    containment_success: float
    rupture_points: list[str]
    integration_rationale: str
    selection_criteria: list[str]
    candidates: list[UtteranceBlueprintSlice]


class WorkingMemorySlice(TypedDict, total=False):
    """In-session transient memory used before long-term persistence."""

    active_themes: list[str]
    salient_user_phrases: list[str]
    retrieved_memory_ids: list[str]
    unresolved_questions: list[str]
    current_episode_summary: str | None
    last_user_intent_prediction: str | None


# ---------------------------------------------------------------------------
# dynamics slice
# ---------------------------------------------------------------------------
class DynamicsSlice(TypedDict, total=False):
    """Turn-local dynamics summary; no longer the source of truth for desire."""

    id_output: dict
    ego_output: dict
    superego_output: dict
    defense_output: dict
    drive_axes: list[DriveAxisSlice]
    target_lock: float
    suppression_risk: float
    affective_pressure: float


# ---------------------------------------------------------------------------
# trace slice
# ---------------------------------------------------------------------------
class TraceSlice(TypedDict, total=False):
    """Debug / research trace."""

    social_cue: dict | None
    appraisal: dict | None
    action_arbitration: dict | None
    utterance_planner: dict | None
    surface_realization: dict | None
    internal_dynamics: dict | None
    supervisor: dict | None
    memory_commit: dict | None
    error: dict | None


# ---------------------------------------------------------------------------
# _internal slice (extends agent-contracts BaseInternalSlice)
# ---------------------------------------------------------------------------
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

    # SplitMind-specific
    session: dict
    event_flags: dict
    errors: list[dict]
    status: str | None
    persistence: dict | None
