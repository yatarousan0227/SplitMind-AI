# Phase 9: Implementation Task List

This document turns the Phase 9 architecture redesign into concrete task groups.

## Purpose

- lock execution order
- make touched files predictable
- keep root-cause work separate from cosmetic fixes
- include Dashboard and evaluation work in the definition of done

## Task Group Order

```mermaid
flowchart LR
    T1["Task Group 1<br/>State + Contracts"] --> T2["Task Group 2<br/>Surface State Node"]
    T2 --> T3["Task Group 3<br/>Supervisor / Planner / Realization Split"]
    T3 --> T4["Task Group 4<br/>Relationship Pacing"]
    T4 --> T5["Task Group 5<br/>Critic + Reranking"]
    T5 --> T6["Task Group 6<br/>Dashboard / Trace UI"]
    T6 --> T7["Task Group 7<br/>Evaluation + QA"]
```

## Intended Use

Read this after the Phase 9 roadmap if you need implementation order rather than design rationale.
