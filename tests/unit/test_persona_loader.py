"""Tests for persona YAML loading."""

import pytest

from splitmind_ai.personas.loader import list_personas, load_persona


def test_list_personas():
    personas = list_personas()
    assert "cold_attached_idol" in personas
    assert "warm_guarded_companion" in personas


def test_load_cold_attached_idol():
    p = load_persona("cold_attached_idol")
    assert p.name == "cold but attached idol"
    assert "id_strength" in p.weights
    assert p.weights["id_strength"] == 0.78
    assert len(p.tone_guardrails) > 0
    assert len(p.prohibited_expressions) > 0


def test_load_warm_guarded_companion():
    p = load_persona("warm_guarded_companion")
    assert p.name == "warm but guarded companion"
    assert p.weights["warmth_recovery_speed"] == 0.72


def test_persona_to_slice():
    p = load_persona("cold_attached_idol")
    s = p.to_slice()
    assert s["persona_name"] == "cold but attached idol"
    assert isinstance(s["weights"], dict)
    assert isinstance(s["defense_biases"], dict)
    assert isinstance(s["tone_guardrails"], list)


def test_load_nonexistent_persona_raises():
    with pytest.raises(FileNotFoundError):
        load_persona("nonexistent_persona")
