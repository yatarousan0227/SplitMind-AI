"""Root agent state combining next-generation SplitMind-AI slices."""

from __future__ import annotations

from typing import TypedDict

from splitmind_ai.state.slices import (
    AppraisalSlice,
    ConflictStateSlice,
    ConversationSlice,
    DriveStateSlice,
    InternalSlice,
    MemorySlice,
    MemoryInterpretationSlice,
    MoodSlice,
    PersonaSlice,
    RelationshipStateSlice,
    RequestSlice,
    ResponseSlice,
    TraceSlice,
    WorkingMemorySlice,
)


class SplitMindAgentState(TypedDict, total=False):
    """Root state passed through the graph."""

    request: RequestSlice
    response: ResponseSlice
    conversation: ConversationSlice
    persona: PersonaSlice
    relationship_state: RelationshipStateSlice
    mood: MoodSlice
    memory: MemorySlice
    appraisal: AppraisalSlice
    conflict_state: ConflictStateSlice
    drive_state: DriveStateSlice
    working_memory: WorkingMemorySlice
    memory_interpretation: MemoryInterpretationSlice
    trace: TraceSlice
    _internal: InternalSlice


CUSTOM_SLICES: list[str] = [
    "request",
    "response",
    "conversation",
    "persona",
    "relationship_state",
    "mood",
    "memory",
    "appraisal",
    "conflict_state",
    "drive_state",
    "working_memory",
    "memory_interpretation",
    "trace",
    "_internal",
]
