"""Root agent state combining next-generation SplitMind-AI slices."""

from __future__ import annotations

from typing import TypedDict

from splitmind_ai.state.slices import (
    AppraisalSlice,
    ComparisonPolicySlice,
    ConflictStateSlice,
    ConversationSlice,
    DriveStateSlice,
    InternalSlice,
    MemorySlice,
    MemoryInterpretationSlice,
    MoodSlice,
    PersonaSlice,
    RelationalPolicySlice,
    RepairPolicySlice,
    ResidueStateSlice,
    RelationshipStateSlice,
    RequestSlice,
    ResponseSlice,
    TraceSlice,
    TurnShapingPolicySlice,
    WorkingMemorySlice,
)


class SplitMindAgentState(TypedDict, total=False):
    """Root state passed through the graph."""

    request: RequestSlice
    response: ResponseSlice
    conversation: ConversationSlice
    persona: PersonaSlice
    relational_policy: RelationalPolicySlice
    relationship_state: RelationshipStateSlice
    mood: MoodSlice
    memory: MemorySlice
    appraisal: AppraisalSlice
    conflict_state: ConflictStateSlice
    turn_shaping_policy: TurnShapingPolicySlice
    repair_policy: RepairPolicySlice
    comparison_policy: ComparisonPolicySlice
    residue_state: ResidueStateSlice
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
    "relational_policy",
    "relationship_state",
    "mood",
    "memory",
    "appraisal",
    "conflict_state",
    "turn_shaping_policy",
    "repair_policy",
    "comparison_policy",
    "residue_state",
    "drive_state",
    "working_memory",
    "memory_interpretation",
    "trace",
    "_internal",
]
