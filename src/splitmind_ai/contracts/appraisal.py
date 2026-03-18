"""Contract schemas for stimulus appraisal in the conflict-engine architecture."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for strict schema contracts."""

    model_config = ConfigDict(extra="forbid")


class RelationalEventType(str, Enum):
    """High-level relational meaning inferred from the user turn."""

    good_news = "good_news"
    exclusive_disclosure = "exclusive_disclosure"
    repair_offer = "repair_offer"
    commitment_request = "commitment_request"
    reassurance = "reassurance"
    distancing = "distancing"
    ambiguity = "ambiguity"
    affection_signal = "affection_signal"
    provocation = "provocation"
    boundary_test = "boundary_test"
    casual_check_in = "casual_check_in"
    unknown = "unknown"


class AppraisalValence(str, Enum):
    """Overall relational valence of the event."""

    positive = "positive"
    negative = "negative"
    mixed = "mixed"
    neutral = "neutral"


class TensionTarget(str, Enum):
    """Which internal axis the event primarily tensions."""

    closeness = "closeness"
    pride = "pride"
    shame = "shame"
    jealousy = "jealousy"
    control = "control"
    safety = "safety"
    status = "status"
    ambiguity = "ambiguity"


class Stakes(str, Enum):
    """How consequential the event appears for the relationship."""

    low = "low"
    medium = "medium"
    high = "high"


class RelationalCue(StrictContractModel):
    """A compact cue extracted from the user turn."""

    label: str
    evidence: str = Field(default="")
    intensity: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class EventMix(StrictContractModel):
    """Mixed-event parse that preserves primary and secondary relational meanings."""

    primary_event: RelationalEventType = Field(default=RelationalEventType.unknown)
    secondary_events: list[RelationalEventType] = Field(default_factory=list)
    comparison_frame: str = Field(default="none")
    repair_signal_strength: float = Field(ge=0.0, le=1.0, default=0.0)
    priority_signal_strength: float = Field(ge=0.0, le=1.0, default=0.0)
    distance_signal_strength: float = Field(ge=0.0, le=1.0, default=0.0)


class RelationalActProfile(StrictContractModel):
    """Continuous relational-act strengths that preserve mixed-turn meaning."""

    affection: float = Field(ge=0.0, le=1.0, default=0.0)
    repair_bid: float = Field(ge=0.0, le=1.0, default=0.0)
    reassurance: float = Field(ge=0.0, le=1.0, default=0.0)
    commitment: float = Field(ge=0.0, le=1.0, default=0.0)
    priority_restore: float = Field(ge=0.0, le=1.0, default=0.0)
    comparison: float = Field(ge=0.0, le=1.0, default=0.0)
    distancing: float = Field(ge=0.0, le=1.0, default=0.0)


class SpeakerIntent(StrictContractModel):
    """User-side intent anchors to keep perspective stable downstream."""

    user_distance_request: bool = Field(default=False)
    user_repair_bid: bool = Field(default=False)
    user_comparison_target: str = Field(default="")
    user_commitment_signal: bool = Field(default=False)
    user_is_describing_own_state: bool = Field(default=False)


class PerspectiveGuard(StrictContractModel):
    """Constraints that preserve subject perspective through downstream nodes."""

    preserve_user_as_subject: bool = Field(default=False)
    disallow_assistant_self_distancing: bool = Field(default=False)
    rationale: str = Field(default="")


class RelationalCueParse(StrictContractModel):
    """LLM-authored pre-appraisal relational cue parse."""

    cues: list[RelationalCue] = Field(default_factory=list)
    event_mix: EventMix = Field(default_factory=EventMix)
    relational_act_profile: RelationalActProfile = Field(default_factory=RelationalActProfile)
    speaker_intent: SpeakerIntent = Field(default_factory=SpeakerIntent)
    perspective_guard: PerspectiveGuard = Field(default_factory=PerspectiveGuard)
    target_hint: TensionTarget = Field(default=TensionTarget.ambiguity)
    valence_hint: AppraisalValence = Field(default=AppraisalValence.neutral)
    stakes_hint: Stakes = Field(default=Stakes.low)
    user_intent_guess: str = Field(default="")
    active_themes: list[str] = Field(default_factory=list)


class StimulusAppraisal(StrictContractModel):
    """Relational interpretation of the latest user turn."""

    event_type: RelationalEventType = Field(default=RelationalEventType.unknown)
    valence: AppraisalValence = Field(default=AppraisalValence.neutral)
    target_of_tension: TensionTarget = Field(default=TensionTarget.ambiguity)
    stakes: Stakes = Field(default=Stakes.low)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    cues: list[RelationalCue] = Field(default_factory=list)
    summary_short: str = Field(default="")
    user_intent_guess: str = Field(default="")
    active_themes: list[str] = Field(default_factory=list)
    event_mix: EventMix = Field(default_factory=EventMix)
    relational_act_profile: RelationalActProfile = Field(default_factory=RelationalActProfile)
    speaker_intent: SpeakerIntent = Field(default_factory=SpeakerIntent)
    perspective_guard: PerspectiveGuard = Field(default_factory=PerspectiveGuard)
