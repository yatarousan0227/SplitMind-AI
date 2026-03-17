"""Logical contract schemas for persona framing and utterance planning."""

from __future__ import annotations

from pydantic import BaseModel, Field

from splitmind_ai.contracts.action_policy import UtteranceCandidate


class ExpressionSettings(BaseModel):
    """Controls the surface presentation of the response."""

    length: str = Field(description="short | medium | long")
    temperature: str = Field(description="cold | cool | warm | hot")
    directness: float = Field(ge=0.0, le=1.0)
    ambiguity: float = Field(ge=0.0, le=1.0)
    sharpness: float = Field(ge=0.0, le=1.0)
    hesitation: float = Field(
        ge=0.0, le=1.0, default=0.2,
        description="How much hesitation, trailing off, or self-interruption appears",
    )
    unevenness: float = Field(
        ge=0.0, le=1.0, default=0.2,
        description="How uneven or imperfectly controlled the surface delivery feels",
    )


class ToneProfile(BaseModel):
    """Tone analysis of the final response."""

    warmth: float = Field(ge=0.0, le=1.0, description="Warmth level")
    tension: float = Field(ge=0.0, le=1.0, description="Underlying tension")
    playfulness: float = Field(ge=0.0, le=1.0, description="Playfulness level")


class PersonaSupervisorFrame(BaseModel):
    """Structured frame the Persona Supervisor prepares before text generation."""

    surface_intent: str = Field(description="What the response overtly communicates")
    hidden_pressure: str = Field(description="What leaks or lingers beneath the surface")
    defense_applied: str = Field(description="Which defense mechanism shaped the output")
    mask_goal: str = Field(
        default="",
        description="What face, self-image, or social mask the persona tries to preserve",
    )
    expression_settings: ExpressionSettings
    tone_profile: ToneProfile = Field(
        default_factory=lambda: ToneProfile(warmth=0.5, tension=0.0, playfulness=0.3),
        description="Tone analysis of the response",
    )
    leakage_level: float = Field(
        ge=0.0, le=1.0, default=0.3,
        description="How much internal pressure leaks into the response",
    )
    containment_success: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="How successfully the persona keeps the mask intact; lower means visible slippage",
    )
    rupture_points: list[str] = Field(
        default_factory=list,
        description="Short notes on where the response slips, overcorrects, or fails to integrate cleanly",
    )
    integration_rationale: str = Field(
        description="Why this balance of reveal/conceal was attempted, including what could not be fully contained"
    )
    integration_rationale_short: str = Field(
        default="",
        description="One-line summary of the integration decision",
    )
    selection_criteria: list[str] = Field(
        default_factory=list,
        description="What the later candidate selector should optimize for",
    )


class UtteranceBlueprint(BaseModel):
    """A candidate direction before the final surface text is written."""

    label: str = Field(description="Short candidate name")
    mode: str = Field(description="Social action mode this blueprint serves")
    opening_style: str = Field(description="How the line should open")
    interpersonal_move: str = Field(description="What social move the line performs")
    latent_signal: str = Field(description="What emotional residue should leak through")
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class UtterancePlan(BaseModel):
    """Bundle of candidate blueprints for later realization/selection."""

    frame: PersonaSupervisorFrame
    candidates: list[UtteranceBlueprint] = Field(min_length=2, max_length=3)


class CombinedPersonaRealization(PersonaSupervisorFrame):
    """Single-call output that includes both the frame and selected surface text."""

    selected_text: str
    selected_index: int = Field(ge=0, default=0)
    candidates: list[UtteranceCandidate] = Field(default_factory=list)
    selection_rationale: str = Field(default="")
    rejected_reasons: list[str] = Field(default_factory=list)
