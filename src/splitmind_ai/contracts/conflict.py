"""Contract schemas for conflict resolution and fidelity gating."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    move_family: str
    move_style: str
    move_rationale: str = Field(default="")
    dominant_compromise: str = Field(default="")
    stability: float = Field(ge=0.0, le=1.0, default=0.5)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_social_move(cls, data):
        if not isinstance(data, dict):
            return data
        if "social_move" in data and "move_style" not in data:
            style = str(data.get("social_move") or "")
            data = dict(data)
            data["move_style"] = style
            data["move_family"] = _infer_move_family(style)
            data.pop("social_move", None)
        elif "move_style" in data and "move_family" not in data:
            data = dict(data)
            data["move_family"] = _infer_move_family(str(data.get("move_style") or ""))
        return data

    @property
    def social_move(self) -> str:
        """Backward-compatible alias for older callers."""
        return self.move_style


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


class RepairPolicy(StrictContractModel):
    """Turn-local repair policy derived from persona style and context."""

    repair_mode: str = Field(default="closed")
    warmth_ceiling: float = Field(ge=0.0, le=1.0, default=0.3)
    status_preservation_requirement: float = Field(ge=0.0, le=1.0, default=0.5)
    required_boundary_marker: bool = Field(default=False)
    followup_pull_allowed: bool = Field(default=False)


class ComparisonPolicy(StrictContractModel):
    """Turn-local comparison / jealousy policy derived from appraisal and residue."""

    comparison_threat_level: float = Field(ge=0.0, le=1.0, default=0.0)
    self_relevance: float = Field(ge=0.0, le=1.0, default=0.0)
    status_injury: float = Field(ge=0.0, le=1.0, default=0.0)
    teasing_allowed: bool = Field(default=False)
    direct_reclaim_allowed: bool = Field(default=False)


class RequiredSurfaceMarkers(StrictContractModel):
    """Surface markers that must appear in the realized response."""

    acknowledge_bid: bool = Field(default=False)
    holdback_marker: bool = Field(default=False)
    boundary_marker: bool = Field(default=False)
    status_marker: bool = Field(default=False)
    pace_marker: bool = Field(default=False)


class ForbiddenCollapses(StrictContractModel):
    """Failure modes that should not be allowed for the current turn."""

    gratitude_only: bool = Field(default=False)
    instant_reciprocity: bool = Field(default=False)
    generic_reassurance: bool = Field(default=False)
    generic_agreement: bool = Field(default=False)
    full_repair_reset: bool = Field(default=False)


class TurnShapingPolicy(StrictContractModel):
    """Shared shaping policy that preserves mixed-turn counterforces."""

    primary_frame: str = Field(default="")
    secondary_frame: str = Field(default="")
    preserved_counterforce: str = Field(default="none")
    warmth_floor: float = Field(ge=0.0, le=1.0, default=0.0)
    warmth_ceiling: float = Field(ge=0.0, le=1.0, default=1.0)
    reciprocity_ceiling: float = Field(ge=0.0, le=1.0, default=1.0)
    disclosure_ceiling: float = Field(ge=0.0, le=1.0, default=1.0)
    required_surface_markers: RequiredSurfaceMarkers = Field(default_factory=RequiredSurfaceMarkers)
    forbidden_collapses: ForbiddenCollapses = Field(default_factory=ForbiddenCollapses)
    followup_pull_allowed: bool = Field(default=False)
    surface_guidance_mode: str = Field(default="none")


class ActiveResidue(StrictContractModel):
    """One short-horizon residue strand that can persist across turns."""

    label: str = Field(default="")
    intensity: float = Field(ge=0.0, le=1.0, default=0.0)
    decay: float = Field(ge=0.0, le=1.0, default=0.5)
    persona_modifier: float = Field(ge=0.0, le=1.0, default=0.5)
    linked_theme: str = Field(default="")
    source_event: str = Field(default="")


class ResidueState(StrictContractModel):
    """Short-horizon residue state carried across turns."""

    active_residues: list[ActiveResidue] = Field(default_factory=list)
    dominant_residue: str = Field(default="")
    overall_load: float = Field(ge=0.0, le=1.0, default=0.0)
    trigger_links: list[str] = Field(default_factory=list)


class FidelityGateResult(StrictContractModel):
    """Structured result of validating a realized response."""

    passed: bool = Field(default=True)
    move_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    residue_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    structural_persona_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    persona_separation_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    repair_style_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    comparison_style_fidelity: float = Field(ge=0.0, le=1.0, default=1.0)
    perspective_integrity: float = Field(ge=0.0, le=1.0, default=1.0)
    flattening_risk: float = Field(ge=0.0, le=1.0, default=0.0)
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


def _infer_move_family(move_style: str) -> str:
    mapping = {
        "accept_but_hold": "repair_acceptance",
        "cool_accept_with_edge": "repair_acceptance",
        "warm_boundaried_accept": "repair_acceptance",
        "accept_from_above": "repair_acceptance",
        "receive_without_chasing": "affection_receipt",
        "defer_without_chasing": "affection_receipt",
        "allow_dependence_but_reframe": "affection_receipt",
        "playful_reclaim": "comparison_response",
        "soft_tease_then_receive": "comparison_response",
        "above_the_frame": "comparison_response",
        "acknowledge_without_opening": "distance_response",
        "firm_boundary_acknowledgment": "distance_response",
        "withdraw": "distance_response",
    }
    return mapping.get(move_style, "boundary_clarification" if move_style else "")
