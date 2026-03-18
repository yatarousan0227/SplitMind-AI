# SplitMind-AI Implementation Plan

This directory breaks the concept specification into implementation phases that can be executed and reviewed in code.

The current plan does not map each theoretical role to a separate LLM call. Instead, it keeps the MVP constraints defined in the concept spec:

1. two LLM calls per turn
2. structured internal dynamics for Id, Ego, Superego, and Defense
3. a single persona supervisor stage for final framing and selection
4. rule-based Python state updates around the model calls

Note:
- the list above describes the original MVP constraint set, not the current runtime snapshot
- the current default runtime has moved to a 3-call path through `InternalDynamicsNode`, `PersonaSupervisorNode`, and `SurfaceRealizationNode`
- `SurfaceStateNode`, `SelectionCriticNode`, and `relationship_pacing` are now part of the standard runtime

## Reading Order

1. [01-foundation-and-contract-model.en.md](./01-foundation-and-contract-model.en.md)
2. [02-runtime-memory-and-ui.en.md](./02-runtime-memory-and-ui.en.md)
3. [03-evaluation-and-hardening.en.md](./03-evaluation-and-hardening.en.md)
4. [04-vault-memory-redesign.en.md](./04-vault-memory-redesign.en.md)
5. [05-indirect-expression-naturalness.en.md](./05-indirect-expression-naturalness.en.md)
6. [06-psychology-agent-fusion-roadmap.en.md](./06-psychology-agent-fusion-roadmap.en.md)
7. [06-implementation-tasklist.en.md](./06-implementation-tasklist.en.md)
8. [07-performance-tension-and-response-length.en.md](./07-performance-tension-and-response-length.en.md)
9. [08-drive-and-instinct-loop.en.md](./08-drive-and-instinct-loop.en.md)
10. [09-human-roughness-and-relationship-pacing.md](./09-human-roughness-and-relationship-pacing.md) (Japanese)
11. [09-implementation-tasklist.en.md](./09-implementation-tasklist.en.md)

## Current Interpretation

The earlier phases describe the foundation that is already reflected in the repository. Later phases increasingly mix historical plan, architectural diagnosis, and implementation snapshot.

Use these documents as:

- architecture rationale
- implementation sequencing notes
- design constraints for future changes
- context for why the codebase looks the way it does today

Phase 9 status:

- Task Group 1-7 implemented
- runtime, Streamlit dashboard, evaluation heuristics, and qualitative QA updated
- qualitative QA reference: [docs/eval/phase9-qualitative-qa.md](../eval/phase9-qualitative-qa.md)
