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
