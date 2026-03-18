"""Contract schemas for dynamic relationship state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for strict schema contracts."""

    model_config = ConfigDict(extra="forbid")


class RelationshipDurableState(StrictContractModel):
    """Relationship history that should persist across sessions."""

    trust: float = Field(ge=0.0, le=1.0, default=0.5)
    intimacy: float = Field(ge=0.0, le=1.0, default=0.3)
    distance: float = Field(ge=0.0, le=1.0, default=0.5)
    attachment_pull: float = Field(ge=0.0, le=1.0, default=0.3)
    relationship_stage: str = Field(default="unfamiliar")
    commitment_readiness: float = Field(ge=0.0, le=1.0, default=0.0)
    repair_depth: float = Field(ge=0.0, le=1.0, default=0.0)
    unresolved_tension_summary: list[str] = Field(default_factory=list)


class RelationshipEphemeralState(StrictContractModel):
    """Transient relationship charge that may decay or be recomputed."""

    tension: float = Field(ge=0.0, le=1.0, default=0.0)
    recent_relational_charge: float = Field(ge=0.0, le=1.0, default=0.0)
    escalation_allowed: bool = Field(default=False)
    interaction_fragility: float = Field(ge=0.0, le=1.0, default=0.0)
    turn_local_repair_opening: float = Field(ge=0.0, le=1.0, default=0.0)
    repair_mode: str = Field(default="closed")


class RelationshipState(StrictContractModel):
    """Complete relationship state for the new architecture."""

    durable: RelationshipDurableState = Field(default_factory=RelationshipDurableState)
    ephemeral: RelationshipEphemeralState = Field(default_factory=RelationshipEphemeralState)
