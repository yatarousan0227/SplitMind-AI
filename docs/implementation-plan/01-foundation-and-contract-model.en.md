# Phase 1: Foundation and Contract Model

## Goal

Translate the high-level concept into durable implementation boundaries.

## Deliverables

1. executable Python project skeleton
2. typed state and contract schemas
3. graph definition based on `agent-contracts`
4. fixed persona definitions and prompt I/O boundaries

## Key Decisions

### Python Version

The project targets Python 3.11+ because the surrounding tooling and contract model assume that baseline.

### Packaging

`uv` is the recommended workflow because fast dependency resolution and reproducibility matter more than tooling variety.

### Architectural Boundary

The critical design choice is to keep internal roles explicit in code and contracts even when they are not separate runtime agents. This prevents the project from collapsing back into a single opaque persona prompt.

## Expected Result

After this phase, the project should have:

- a stable repository layout
- state slices that can be reasoned about independently
- contracts that enforce structure at LLM boundaries
- a graph foundation that later phases can extend without rewriting everything
