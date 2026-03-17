# Phase 3: Evaluation and Hardening

## Goal

Move from an interesting proof of concept to a system that can be compared, tested, and maintained.

## Main Focus

1. baseline comparisons
2. explicit safety boundaries
3. stronger observability and maintainability

## Baselines

At minimum, compare against:

- single-persona bot
- persona plus memory bot
- emotion-label response system
- multi-agent bot without psychodynamic role modeling

These baselines help isolate what SplitMind-specific structure is actually buying.

## Expected Outcome

After this phase, the project should be able to say more than "this feels interesting." It should be able to say:

- what it outperforms
- what it fails at
- how risky outputs are bounded
- how to inspect internal failures after the fact
