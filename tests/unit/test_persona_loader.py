"""Tests for v2 persona YAML loading."""

import pytest

from splitmind_ai.personas.loader import list_personas, load_persona


def test_list_personas():
    personas = list_personas()
    assert "cold_attached_idol" in personas
    assert "warm_guarded_companion" in personas


def test_load_cold_attached_idol():
    p = load_persona("cold_attached_idol")
    assert p.name == "cold_attached_idol"
    assert p.psychodynamics["drives"]["closeness"] == pytest.approx(0.72)
    assert p.relational_profile["attachment_pattern"] == "avoidant_leaning"
    assert p.safety_boundary["hard_limits"]["max_direct_neediness"] == pytest.approx(0.18)


def test_load_warm_guarded_companion():
    p = load_persona("warm_guarded_companion")
    assert p.name == "warm_guarded_companion"
    assert p.ego_organization["warmth_recovery_speed"] == pytest.approx(0.72)
    assert p.relational_profile["default_role_frame"] == "protective_pair"


def test_persona_to_slice():
    p = load_persona("cold_attached_idol")
    s = p.to_slice()
    assert s["persona_version"] == 2
    assert isinstance(s["psychodynamics"], dict)
    assert isinstance(s["defense_organization"], dict)
    assert isinstance(s["safety_boundary"]["hard_limits"], dict)


def test_load_nonexistent_persona_raises():
    with pytest.raises(FileNotFoundError):
        load_persona("nonexistent_persona")
