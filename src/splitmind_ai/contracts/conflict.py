"""Contract schemas for conflict resolution and fidelity gating."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for strict schema contracts."""

    model_config = ConfigDict(extra="forbid")


class IdImpulse(StrictContractModel):
    """Immediate wants activated by the current user turn."""

    dominant_want: str
    secondary_wants: list[str] = Field(default_factory=list)
    intensity: float = Field(ge=0.0, le=1.0)
    target: str = Field(default="")


class SuperegoPressure(StrictContractModel):
    """Constraints and self-image pressures active on this turn."""

    forbidden_moves: list[str] = Field(default_factory=list)
    self_image_to_protect: str = Field(default="")
    pressure: float = Field(ge=0.0, le=1.0)
    shame_load: float = Field(ge=0.0, le=1.0, default=0.0)


class EgoMove(StrictContractModel):
    """Integrated social move selected for this turn."""

    social_move: str
    move_rationale: str = Field(default="")
    dominant_compromise: str = Field(default="")
    stability: float = Field(ge=0.0, le=1.0, default=0.5)


class Residue(StrictContractModel):
    """What leaks through after partial containment."""

    visible_emotion: str
    leak_channel: str = Field(default="")
    residue_text_intent: str = Field(default="")
    intensity: float = Field(ge=0.0, le=1.0, default=0.5)


class ExpressionEnvelope(StrictContractModel):
    """Low-dimensional rendering constraints derived from the conflict outcome."""

    length: str = Field(description="short | medium | long")
    temperature: str = Field(description="cold | cool_warm | warm | hot")
    directness: float = Field(ge=0.0, le=1.0)
    closure: float = Field(ge=0.0, le=1.0)


class ConflictState(StrictContractModel):
    """Complete output of the conflict engine for a single turn."""

    id_impulse: IdImpulse
    superego_pressure: SuperegoPressure
    ego_move: EgoMove
    residue: Residue
    expression_envelope: ExpressionEnvelope


class FidelityGateResult(StrictContractModel):
    """Structured result of validating a realized response."""

    passed: bool = Field(default=True)
    move_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    residue_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    structural_persona_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    anti_exposition: float = Field(ge=0.0, le=1.0, default=1.0)
    hard_safety: float = Field(ge=0.0, le=1.0, default=1.0)
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str = Field(default="")


class ExpressionRealization(StrictContractModel):
    """Single realized reply derived from conflict outcome."""

    text: str
    rationale_short: str = Field(default="")
    move_alignment: str = Field(default="")
    residue_handling: str = Field(default="")


class ConflictMemorySummary(StrictContractModel):
    """Compact turn summary to persist in working memory or long-term memory."""

    event_type: str
    ego_move: str
    residue: str
    user_impact: str = Field(default="")
    relationship_delta: str = Field(default="")
