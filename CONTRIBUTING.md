# Contributing

Thanks for contributing to SplitMind-AI.

## Scope

This repository is a research-oriented codebase. Contributions are most useful when they improve one of these areas:

- runtime correctness and graph behavior
- structured contracts and state transitions
- evaluation quality and reproducibility
- safety guardrails
- memory persistence and observability
- documentation clarity

## Before You Start

- Read [README.md](./README.md) for project overview and setup.
- Prefer small, focused pull requests.
- Open an issue first for large behavior changes, architecture changes, or new personas.
- Keep changes aligned with the current design direction: structured internal dynamics, explicit state, and debuggable traces.

## Development Setup

```bash
uv sync --all-extras
cp .env.example .env
```

## Common Commands

```bash
uv run pytest tests/unit -q
uv run pytest tests/ -v
make ci
```

If your change touches runtime behavior, safety logic, prompts, or reporting, add or update tests where practical.

## Pull Request Expectations

- Explain the problem and why the change is needed.
- Describe behavioral impact, not just implementation details.
- Include tests or a clear reason tests were not added.
- Update documentation when user-facing behavior, setup, or architecture changes.
- Keep unrelated refactors out of the same pull request.

## Coding Notes

- Python 3.11+ is the baseline.
- Follow the existing project structure under `src/splitmind_ai/`.
- Preserve typed contracts and explicit state boundaries.
- Favor changes that keep traces and evaluation outputs inspectable.

## Commit and Review Guidance

- Use clear commit messages.
- Reviewers will prioritize regressions in runtime flow, safety behavior, memory writes, and evaluation comparability.
- Maintainers may ask to split large PRs before review.

## Licensing

By submitting a contribution, you agree that your contribution will be licensed under the Apache License 2.0 that covers this repository.
