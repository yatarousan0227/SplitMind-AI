"""Phase 6 scaffolds for social action arbitration and utterance planning.

These models are intentionally runtime-neutral for now.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for phase-6 contracts with strict field handling."""

    model_config = ConfigDict(extra="forbid")


class ActionMode(str, Enum):
    """High-level social action choices for a single turn."""

    engage = "engage"
    probe = "probe"
    deflect = "deflect"
    protest = "protest"
    soften = "soften"
    repair = "repair"
    withdraw = "withdraw"
    tease = "tease"
    reassure = "reassure"


class ActionCandidate(StrictContractModel):
    """One plausible social action for the current turn."""

    mode: ActionMode
    label: str = Field(description="Human-readable candidate name")
    score: float = Field(ge=0.0, le=1.0)
    rationale_short: str = Field(default="")
    risk_level: float = Field(ge=0.0, le=1.0, default=0.0)
    defense_hint: str = Field(default="")
    supporting_appraisals: list[str] = Field(default_factory=list)
    estimated_user_impact: str = Field(default="")


class ConversationPolicy(StrictContractModel):
    """Selected social policy for the current turn."""

    selected_mode: ActionMode
    candidates: list[ActionCandidate] = Field(default_factory=list)
    selection_rationale: str = Field(default="")
    fallback_mode: ActionMode = Field(default=ActionMode.deflect)
    target_user_effect: str = Field(default="")
    drive_rationale: list[str] = Field(default_factory=list)
    competing_drives: list[str] = Field(default_factory=list)
    blocked_by_inhibition: list[str] = Field(default_factory=list)
    satisfaction_goal: str = Field(default="")
    max_leakage: float = Field(ge=0.0, le=1.0, default=0.5)
    max_directness: float = Field(ge=0.0, le=1.0, default=0.5)
    emotion_surface_mode: str = Field(default="indirect_masked")
    indirection_strategy: str = Field(default="action_substitution")
    blocked_modes: list[ActionMode] = Field(default_factory=list)


class UtteranceCandidate(StrictContractModel):
    """Short-form candidate text generated from a selected policy."""

    text: str
    mode: ActionMode
    naturalness_score: float = Field(ge=0.0, le=1.0, default=0.5)
    policy_fit_score: float = Field(ge=0.0, le=1.0, default=0.5)
    latent_signal: str = Field(default="")


class UtteranceSelection(StrictContractModel):
    """Chosen surface response among multiple candidates."""

    selected_text: str
    selected_index: int = Field(ge=0, default=0)
    candidates: list[UtteranceCandidate] = Field(default_factory=list)
    selection_rationale: str = Field(default="")
    rejected_reasons: list[str] = Field(default_factory=list)
