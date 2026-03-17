# Phase 7: Performance, Tension Decay, and Response-Length Control

## Goal

Improve the user experience without flattening the personality model.

## Problems To Solve

1. responses are too slow
2. `tension` and `active_themes` can persist too long
3. some situations produce replies that are too short

## Main Direction

This phase focuses on:

- reducing unnecessary runtime overhead
- decaying pressure so the system does not remain stuck in one state
- controlling response length so short replies feel intentional rather than accidental

## Design Constraint

Performance fixes should not collapse the architecture back into an unstructured single-pass assistant. The goal is a faster and more stable experience while keeping explicit internal pressure meaningful.
