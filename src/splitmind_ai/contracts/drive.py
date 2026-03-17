"""Drive-state contracts for motivational persistence.

These models define the persistent motivational state introduced in Phase 8.
They are runtime-neutral and can be adopted incrementally by nodes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for strict contracts with no unknown fields."""

    model_config = ConfigDict(extra="forbid")


class DriveAxis(StrictContractModel):
    """One drive signal with optional target and regulation metadata."""

    name: str = Field(description="Drive axis label")
    value: float = Field(ge=0.0, le=1.0)
    target: str | None = Field(default=None)
    urgency: float = Field(ge=0.0, le=1.0, default=0.0)
    frustration: float = Field(ge=0.0, le=1.0, default=0.0)
    satiation: float = Field(ge=0.0, le=1.0, default=0.0)
    carryover: float = Field(ge=0.0, le=1.0, default=0.0)
    suppression_load: float = Field(ge=0.0, le=1.0, default=0.0)


class DriveState(StrictContractModel):
    """Persistent motivational state used as the source of truth."""

    drive_vector: dict[str, float] = Field(default_factory=dict)
    top_drives: list[DriveAxis] = Field(default_factory=list)
    drive_targets: dict[str, str] = Field(default_factory=dict)
    frustration_vector: dict[str, float] = Field(default_factory=dict)
    satiation_vector: dict[str, float] = Field(default_factory=dict)
    suppression_vector: dict[str, float] = Field(default_factory=dict)
    carryover_vector: dict[str, float] = Field(default_factory=dict)
    last_satisfied_drive: str | None = Field(default=None)
    last_blocked_drive: str | None = Field(default=None)
    summary_short: str = Field(default="")


class InhibitionState(StrictContractModel):
    """Turn-level inhibition and self-protective constraints."""

    role_pressure: float = Field(ge=0.0, le=1.0, default=0.0)
    face_preservation: float = Field(ge=0.0, le=1.0, default=0.0)
    dependency_fear: float = Field(ge=0.0, le=1.0, default=0.0)
    pride_level: float = Field(ge=0.0, le=1.0, default=0.0)
    allowed_modes: list[str] = Field(default_factory=list)
    blocked_modes: list[str] = Field(default_factory=list)
    preferred_defenses: list[str] = Field(default_factory=list)
    blocked_drives: list[str] = Field(default_factory=list)


class MotivationalUpdate(StrictContractModel):
    """Rule-based update payload that mutates persistent drive state."""

    top_drives: list[DriveAxis] = Field(default_factory=list)
    changed_drives: list[str] = Field(default_factory=list)
    satisfaction_events: list[str] = Field(default_factory=list)
    blocked_drives: list[str] = Field(default_factory=list)
    notes: str = Field(default="")
