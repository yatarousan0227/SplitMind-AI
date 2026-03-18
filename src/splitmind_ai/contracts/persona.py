"""Contract schemas for next-generation persona structure."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model for strict schema contracts."""

    model_config = ConfigDict(extra="forbid")


class Identity(StrictContractModel):
    """Human-facing identity information for the persona."""

    self_name: str
    display_name: str | None = None


class Psychodynamics(StrictContractModel):
    """Static motivational and superego priors."""

    drives: dict[str, float] = Field(default_factory=dict)
    threat_sensitivity: dict[str, float] = Field(default_factory=dict)
    superego_configuration: dict[str, float] = Field(default_factory=dict)


class RelationalProfile(StrictContractModel):
    """Static priors for how the persona relates to others."""

    attachment_pattern: str
    default_role_frame: str
    intimacy_regulation: dict[str, float] = Field(default_factory=dict)
    trust_dynamics: dict[str, float] = Field(default_factory=dict)
    dependency_model: dict[str, float] = Field(default_factory=dict)
    exclusivity_orientation: dict[str, float] = Field(default_factory=dict)
    repair_orientation: dict[str, float] = Field(default_factory=dict)


class DefenseOrganization(StrictContractModel):
    """Preferred defenses and decompensation tendencies."""

    primary_defenses: dict[str, float] = Field(default_factory=dict)
    secondary_defenses: dict[str, float] = Field(default_factory=dict)


class EgoOrganization(StrictContractModel):
    """Capacities that shape integration and regulation."""

    affect_tolerance: float = Field(ge=0.0, le=1.0)
    impulse_regulation: float = Field(ge=0.0, le=1.0)
    ambivalence_capacity: float = Field(ge=0.0, le=1.0)
    mentalization: float = Field(ge=0.0, le=1.0)
    self_observation: float = Field(ge=0.0, le=1.0)
    self_disclosure_tolerance: float = Field(ge=0.0, le=1.0)
    warmth_recovery_speed: float = Field(ge=0.0, le=1.0)


class SafetyBoundary(StrictContractModel):
    """Hard limits that the persona should not violate."""

    hard_limits: dict[str, float] = Field(default_factory=dict)


class RelationalPolicy(StrictContractModel):
    """Persona-specific relational negotiation policy."""

    repair_style: str = Field(default="guarded")
    comparison_style: str = Field(default="withhold")
    distance_management_style: str = Field(default="respect_space")
    status_maintenance_style: str = Field(default="medium")
    warmth_release_style: str = Field(default="measured")
    priority_response_style: str = Field(default="implicit")
    residue_persistence: dict[str, float] = Field(default_factory=dict)


class PersonaProfile(StrictContractModel):
    """Complete persona contract for the conflict-engine architecture."""

    persona_version: int = Field(default=2)
    identity: Identity
    gender: Literal["male", "female", "other"]
    psychodynamics: Psychodynamics
    relational_profile: RelationalProfile
    defense_organization: DefenseOrganization
    ego_organization: EgoOrganization
    safety_boundary: SafetyBoundary
    relational_policy: RelationalPolicy = Field(default_factory=RelationalPolicy)
