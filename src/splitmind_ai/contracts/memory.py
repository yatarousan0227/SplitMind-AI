"""Schemas for memory persistence artifacts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UnresolvedTension(BaseModel):
    """A single unresolved emotional tension."""

    theme: str
    intensity: float = Field(ge=0.0, le=1.0)
    source: str
    created_at: datetime = Field(default_factory=datetime.now)


class SessionSummary(BaseModel):
    """Concise summary of a completed session."""

    session_id: str
    summary: str
    turn_count: int
    dominant_mood: str
    key_events: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class EmotionalMemory(BaseModel):
    """An emotionally significant event worth persisting."""

    event: str
    emotion: str
    intensity: float = Field(ge=0.0, le=1.0)
    trigger: str | None = None
    target: str | None = None
    wound: str | None = None
    blocked_action: str | None = None
    attempted_action: str | None = None
    action_tendency: str | None = None
    interaction_outcome: str | None = None
    residual_drive: str | None = None
    agent_response: str | None = None
    session_id: str | None = None
    turn_number: int | None = None
    context: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class SemanticPreference(BaseModel):
    """A stable user preference or reaction pattern."""

    topic: str
    preference: str
    evidence: str | None = None
    episode_hint: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    created_at: datetime = Field(default_factory=datetime.now)
