"""Root agent state combining all slices."""

from __future__ import annotations

from typing import TypedDict

from splitmind_ai.state.slices import (
    AppraisalSlice,
    ConversationSlice,
    ConversationPolicySlice,
    DynamicsSlice,
    DriveStateSlice,
    InhibitionStateSlice,
    InternalSlice,
    MemorySlice,
    MoodSlice,
    PersonaSlice,
    RelationshipSlice,
    RequestSlice,
    ResponseSlice,
    SelfStateSlice,
    SocialModelSlice,
    TraceSlice,
    UtterancePlanSlice,
    WorkingMemorySlice,
)


class SplitMindAgentState(TypedDict, total=False):
    """Root state passed through the agent-contracts graph.

    Each key corresponds to a named slice that nodes declare in
    their ``reads`` / ``writes`` contracts.
    """

    request: RequestSlice
    response: ResponseSlice
    conversation: ConversationSlice
    persona: PersonaSlice
    relationship: RelationshipSlice
    mood: MoodSlice
    memory: MemorySlice
    appraisal: AppraisalSlice
    social_model: SocialModelSlice
    self_state: SelfStateSlice
    drive_state: DriveStateSlice
    inhibition_state: InhibitionStateSlice
    conversation_policy: ConversationPolicySlice
    utterance_plan: UtterancePlanSlice
    working_memory: WorkingMemorySlice
    dynamics: DynamicsSlice
    trace: TraceSlice
    _internal: InternalSlice


# All custom slice names that must be registered with the NodeRegistry.
CUSTOM_SLICES: list[str] = [
    "request",
    "response",
    "conversation",
    "persona",
    "relationship",
    "mood",
    "memory",
    "appraisal",
    "social_model",
    "self_state",
    "drive_state",
    "inhibition_state",
    "conversation_policy",
    "utterance_plan",
    "working_memory",
    "dynamics",
    "trace",
    "_internal",
]
