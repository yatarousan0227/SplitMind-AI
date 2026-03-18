# Guides

`guides/` contains practical documentation for people who want to use, inspect, or extend SplitMind-AI without starting from the full concept spec.

```mermaid
flowchart LR
    A["guides/concept.en.md"] --> B["guides/streamlit-ui.en.md"]
    B --> C["guides/implementation-overview.en.md"]
    C --> D["docs/concept.en.md / docs/implementation-plan/README.en.md"]
```

## What This Directory Is For

- learn the core idea quickly before reading the full spec
- understand how to inspect the Streamlit UI
- get an implementation-oriented map of the current codebase
- understand the Phase 9 additions around surface state, pacing, and critic reranking

## Recommended Reading Order

1. [concept.en.md](./concept.en.md)
2. [streamlit-ui.en.md](./streamlit-ui.en.md)
3. [implementation-overview.en.md](./implementation-overview.en.md)

## Guide Index

- [concept.en.md](./concept.en.md)
  Brief explanation of the problem SplitMind-AI is trying to solve and the core modeling idea.
- [streamlit-ui.en.md](./streamlit-ui.en.md)
  How to launch and inspect the Streamlit research UI, especially the dashboard after the Phase 9 surface/pacing/critic updates.
- [implementation-overview.en.md](./implementation-overview.en.md)
  How a turn moves through the current runtime, including planning, critic reranking, and realization.

## Longer References

- [README.md](../README.md)
- [README.ja.md](../README.ja.md)
- [docs/concept.en.md](../docs/concept.en.md)
- [docs/concept.md](../docs/concept.md)
- [docs/implementation-plan/README.en.md](../docs/implementation-plan/README.en.md)
- [docs/implementation-plan/README.md](../docs/implementation-plan/README.md)
- [docs/eval/phase9-qualitative-qa.md](../docs/eval/phase9-qualitative-qa.md)
