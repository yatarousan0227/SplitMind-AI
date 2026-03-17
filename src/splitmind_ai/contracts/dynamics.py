"""Logical contract schemas for internal dynamics (Call 1).

These Pydantic models define the structured output that the LLM must
return during the internal reasoning phase. They are *not* agent-contracts
NodeContracts -- those live on the node classes themselves.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from splitmind_ai.contracts.drive import DriveAxis


class DesireCandidate(BaseModel):
    """A single raw desire hypothesis from the Id."""

    desire_type: str = Field(description="Type of desire (e.g., jealousy, approval_seeking)")
    intensity: float = Field(ge=0.0, le=1.0, description="0-1 intensity")
    target: str = Field(description="Object of the desire")
    direction: str = Field(description="approach | avoid | control | disclose | conceal")
    rationale: str = Field(description="Brief reason this desire was generated")


class IdOutput(BaseModel):
    """Id module output: raw desire candidates and affective pressure."""

    raw_desire_candidates: list[DesireCandidate] = Field(min_length=1)
    drive_axes: list[DriveAxis] = Field(
        min_length=1,
        description="Normalized drive-axis hypotheses used by motivational state updates",
    )
    affective_pressure_score: float = Field(ge=0.0, le=1.0)
    approach_avoidance_balance: float = Field(
        ge=0.0,
        le=1.0,
        description="0 = full avoidance, 1 = full approach",
    )
    target_lock: float = Field(
        ge=0.0,
        le=1.0,
        description="How strongly the current pressure is locked to a single target",
    )
    suppression_risk: float = Field(
        ge=0.0,
        le=1.0,
        description="How likely the current pressure is to be pushed underground",
    )
    impulse_summary: str


class EgoOutput(BaseModel):
    """Ego module output: mediation strategy."""

    response_strategy: str = Field(description="High-level strategy label")
    risk_assessment: str = Field(description="Perceived relational risk")
    concealment_or_reveal_plan: str = Field(
        description="What to hide vs. partially show"
    )
    softening_note: str | None = Field(
        default=None, description="How to soften or delay expression"
    )


class SuperegoOutput(BaseModel):
    """Superego module output: norm evaluation."""

    role_alignment_score: float = Field(ge=0.0, le=1.0)
    ideal_self_gap: float = Field(ge=0.0, le=1.0, description="Deviation from ideal self")
    shame_or_guilt_pressure: float = Field(ge=0.0, le=1.0)
    violation_flags: list[str] = Field(default_factory=list)
    norm_note: str | None = None


class DefenseOutput(BaseModel):
    """Defense mechanism selection."""

    selected_mechanism: str = Field(
        description=(
            "One of: suppression, rationalization, projection, "
            "reaction_formation, displacement, sublimation, "
            "avoidance, ironic_deflection, partial_disclosure. "
            "MUST be chosen based on persona defense_biases — "
            "prefer mechanisms with higher bias values. "
            "partial_disclosure is NOT a universal default."
        )
    )
    transformation_note: str = Field(
        description="How the defense transforms the raw impulse"
    )
    leakage_recommendation: float = Field(
        ge=0.0, le=1.0, description="Suggested leakage amount"
    )


class EventFlags(BaseModel):
    """Fixed event flags for OpenAI-compatible structured output."""

    reassurance_received: bool = False
    rejection_signal: bool = False
    jealousy_trigger: bool = False
    affectionate_exchange: bool = False
    prolonged_avoidance: bool = False
    user_praised_third_party: bool = False
    repair_attempt: bool = False


class InternalDynamicsBundle(BaseModel):
    """Combined output of Call 1 (internal dynamics reasoning).

    This is the full structured JSON the LLM returns in a single call.
    """

    id_output: IdOutput
    ego_output: EgoOutput
    superego_output: SuperegoOutput
    defense_output: DefenseOutput
    dominant_desire: str = Field(
        default="",
        description="Legacy summary label retained only for transitional reporting",
    )
    llm_rationale_short: str = Field(
        default="",
        description="One-sentence summary of the internal reasoning",
    )
    event_flags: EventFlags = Field(
        default_factory=EventFlags,
        description=(
            "Detected event flags for state update rules: "
            "reassurance_received, rejection_signal, jealousy_trigger, "
            "affectionate_exchange, prolonged_avoidance, "
            "user_praised_third_party, repair_attempt"
        ),
    )
