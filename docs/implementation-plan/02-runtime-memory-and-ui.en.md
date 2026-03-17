# Phase 2: Runtime, Memory, and UI

## Goal

Reach a minimum implementation that is usable for research.

## Completion Line

1. one-turn execution is stable
2. relationship, mood, and unresolved tension update across turns
3. long-term memory is written into the vault
4. the research UI can expose the main traces

## Runtime Shape

The early MVP flow is:

1. `SessionBootstrapNode`
2. `InternalDynamicsNode`
3. `PersonaSupervisorNode`
4. `MemoryCommitNode`

Later phases extend this into the fuller graph now present in the repository.

## Why This Phase Matters

This is where the project stops being a pure design document and becomes an executable research system:

- there is a repeatable runtime
- memory survives outside one process
- the UI makes internal behavior observable

Without this phase, later tuning would be guesswork.
