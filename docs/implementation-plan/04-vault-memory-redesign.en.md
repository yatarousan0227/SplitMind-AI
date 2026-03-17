# Phase 4: Vault Memory Redesign

## Goal

Redesign and complete the vault persistence layer so memory continuity survives across sessions.

## Problems Identified

- session summaries were not actually being written
- mood state was resetting between sessions
- semantic preference generation was missing
- emotional memory storage was too coarse to reuse
- `user_sensitivities` stayed empty

## Why The Redesign Was Needed

The earlier vault layer stored some artifacts but did not yet support meaningful continuity. A research system that claims relational persistence cannot treat memory as optional bookkeeping.

## Target Outcome

The vault should support:

- reliable relationship snapshots
- session summaries that are actually written
- reusable emotional memory entries
- semantic preference extraction
- better continuity for later appraisal and response policy
