# Phase 5: Indirect Expression and Naturalness

## Problem

The system could still sound too explicitly explanatory even when internal state suggested guarded or indirect behavior.

Example failure mode:

```text
User: "Hello."
AI: "Hello. I'm happy you came, just a little."
```

When the state says containment is high and directness is low, directly naming the emotion still sounds artificial.

## Main Claim

Human-sounding expression often leaks through:

- action
- topic shift
- silence or temperature gap
- reverse-valence phrasing
- practical care that reveals underlying concern

Not every emotion should be named directly.

## Objective

Make indirect expression a first-class surface strategy rather than an afterthought.

## Resulting Direction

This phase motivates the prompt and realization changes that encourage:

- lower direct naming of emotions
- stronger mapping from defense to surface form
- more believable guarded personas
- explicit exceptions where direct disclosure is more natural than indirection
