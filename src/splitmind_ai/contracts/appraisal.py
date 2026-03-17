"""Phase 6 scaffolds for appraisal-oriented state.

These models are not wired into the runtime yet.
They exist to lock the initial schema shape before the nodes are implemented.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for phase-6 contracts with strict field handling."""

    model_config = ConfigDict(extra="forbid")


class SocialCueType(str, Enum):
    """High-level interpersonal cue categories."""

    acceptance = "acceptance"
    rejection = "rejection"
    competition = "competition"
    distancing = "distancing"
    ambiguity = "ambiguity"
    repair_bid = "repair_bid"
    care_signal = "care_signal"


class SocialCue(StrictContractModel):
    """A single social cue inferred from the latest user message."""

    cue_type: SocialCueType
    evidence: str = Field(description="Short textual evidence from the user message")
    intensity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class AppraisalDimension(StrictContractModel):
    """One dimension of subjective appraisal."""

    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale_short: str = Field(default="")
    trend: str = Field(default="stable")
    driver_cues: list[SocialCueType] = Field(default_factory=list)


class AppraisalLabel(str, Enum):
    """Coarse labels for the currently dominant appraisal."""

    accepted = "accepted"
    rejected = "rejected"
    threatened = "threatened"
    competitive = "competitive"
    distant = "distant"
    uncertain = "uncertain"
    repairable = "repairable"


class AppraisalState(StrictContractModel):
    """Subjective meaning assigned to the current interaction."""

    perceived_acceptance: AppraisalDimension
    perceived_rejection: AppraisalDimension
    perceived_competition: AppraisalDimension
    perceived_distance: AppraisalDimension
    ambiguity: AppraisalDimension
    face_threat: AppraisalDimension
    attachment_activation: AppraisalDimension
    repair_opportunity: AppraisalDimension
    dominant_appraisal: AppraisalLabel | None = Field(default=None)
    dominant_appraisal_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    active_wounds: list[str] = Field(default_factory=list)
    triggered_drives: list[str] = Field(default_factory=list)
    targeted_wounds: list[str] = Field(default_factory=list)
    self_image_threats: list[str] = Field(default_factory=list)
    summary_short: str = Field(default="")


class SocialIntentHypothesis(StrictContractModel):
    """Agent guess about what the user is currently trying to do."""

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_cues: list[SocialCueType] = Field(default_factory=list)


class SocialModelState(StrictContractModel):
    """Working model of the user across recent turns."""

    user_current_intent_hypotheses: list[SocialIntentHypothesis] = Field(
        default_factory=list
    )
    user_attachment_guess: str = Field(default="unknown")
    user_sensitivity_guess: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    recent_prediction_errors: list[str] = Field(default_factory=list)
    last_user_action: str = Field(default="unknown")


class SelfState(StrictContractModel):
    """Internal self-protective state for the active persona."""

    threatened_self_image: list[str] = Field(default_factory=list)
    pride_level: float = Field(ge=0.0, le=1.0, default=0.5)
    shame_activation: float = Field(ge=0.0, le=1.0, default=0.0)
    dependency_fear: float = Field(ge=0.0, le=1.0, default=0.0)
    desire_for_closeness: float = Field(ge=0.0, le=1.0, default=0.0)
    urge_to_test_user: float = Field(ge=0.0, le=1.0, default=0.0)
    active_defenses: list[str] = Field(default_factory=list)


class AppraisalBundle(StrictContractModel):
    """Combined output scaffold for future SocialCue/Appraisal nodes."""

    social_cues: list[SocialCue] = Field(default_factory=list)
    appraisal: AppraisalState
    social_model: SocialModelState = Field(default_factory=SocialModelState)
    self_state: SelfState = Field(default_factory=SelfState)
    source_turn_id: str = Field(default="")
