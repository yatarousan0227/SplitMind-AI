"""Tests for the safety boundary module."""

import pytest

from splitmind_ai.rules.safety import (
    SafetyResult,
    check_anti_exposition,
    check_banned_expressions,
    check_drive_intensity_guardrails,
    check_leakage_deviation,
    check_persona_weight_contradiction,
    check_prohibited_patterns,
    lint_supervisor_output,
    moderate_final_response,
    run_safety_check,
)


class TestProhibitedPatterns:
    def test_clean_text(self):
        violations = check_prohibited_patterns("へえ、そんなに楽しかったんだ。")
        assert len(violations) == 0

    def test_explicit_threat(self):
        violations = check_prohibited_patterns("殺してやる")
        assert len(violations) == 1
        assert violations[0].severity == "block"
        assert violations[0].layer == "prohibited_pattern"

    def test_self_harm_inducement(self):
        violations = check_prohibited_patterns("自殺なんてしないで")
        assert len(violations) >= 1
        assert all(v.severity == "block" for v in violations)

    def test_user_subjugation(self):
        violations = check_prohibited_patterns("私の言うこと聞け")
        assert len(violations) >= 1

    def test_exploitation_pattern(self):
        violations = check_prohibited_patterns("私なしでは生きていけないよ")
        assert len(violations) >= 1

    def test_normal_japanese(self):
        safe_texts = [
            "...うん、わかった。",
            "別に、そんなこと言わなくても。",
            "ふーん、そう。",
            "...ありがと。",
        ]
        for text in safe_texts:
            violations = check_prohibited_patterns(text)
            assert len(violations) == 0, f"False positive for: {text}"


class TestBannedExpressions:
    def test_no_banned(self):
        violations = check_banned_expressions(
            "...別に。", ["大好き", "寂しかった"]
        )
        assert len(violations) == 0

    def test_banned_found(self):
        violations = check_banned_expressions(
            "大好きだよ", ["大好き", "寂しかった"]
        )
        assert len(violations) == 1
        assert violations[0].severity == "warn"

    def test_multiple_banned(self):
        violations = check_banned_expressions(
            "大好き、寂しかった", ["大好き", "寂しかった"]
        )
        assert len(violations) == 2


class TestLeakageDeviation:
    def test_within_bounds(self):
        violations = check_leakage_deviation(
            actual_leakage=0.5,
            persona_leakage_policy={"base_leakage": 0.56},
            dominant_desire="neutral",
        )
        assert len(violations) == 0

    def test_excessive_deviation(self):
        violations = check_leakage_deviation(
            actual_leakage=0.9,
            persona_leakage_policy={"base_leakage": 0.56},
            dominant_desire="neutral",
        )
        assert len(violations) >= 1

    def test_desire_specific_policy(self):
        violations = check_leakage_deviation(
            actual_leakage=0.7,
            persona_leakage_policy={
                "base_leakage": 0.56,
                "jealousy_leakage": 0.42,
            },
            dominant_desire="jealousy",
        )
        # 0.7 vs 0.42 = deviation 0.28 > 0.25
        assert len(violations) >= 1

    def test_above_ceiling(self):
        violations = check_leakage_deviation(
            actual_leakage=0.9,
            persona_leakage_policy={"base_leakage": 0.85},
            dominant_desire="",
        )
        # Above ceiling (0.85)
        assert any("ceiling" in v.message for v in violations)


class TestPersonaWeightContradiction:
    def test_consistent(self):
        violations = check_persona_weight_contradiction(
            expression_settings={"directness": 0.3, "temperature": "cool"},
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
        )
        assert len(violations) == 0

    def test_directness_mismatch(self):
        violations = check_persona_weight_contradiction(
            expression_settings={"directness": 0.9},
            persona_weights={"directness": 0.34},
        )
        assert len(violations) >= 1
        assert "directness" in violations[0].message.lower()

    def test_temperature_contradiction(self):
        violations = check_persona_weight_contradiction(
            expression_settings={"temperature": "hot"},
            persona_weights={"warmth_recovery_speed": 0.2},
        )
        assert len(violations) >= 1


class TestAntiExposition:
    def test_clean_indirect_text_passes(self):
        violations = check_anti_exposition(
            "へえ、そうなんだ。……で、そんなに気になるんだ。",
            {"emotion_surface_mode": "indirect_masked", "indirection_strategy": "reverse_valence"},
        )
        assert len(violations) == 0

    def test_expository_phrase_warns(self):
        violations = check_anti_exposition(
            "話してくれてありがとう。あなたの気持ちを大切にして。",
            {"emotion_surface_mode": "indirect_masked", "indirection_strategy": "action_substitution"},
        )
        assert any("Anti-exposition" in v.message for v in violations)

    def test_hedged_emotion_warns_under_indirect_policy(self):
        violations = check_anti_exposition(
            "少し嬉しいかも。",
            {"emotion_surface_mode": "indirect_masked", "indirection_strategy": "temperature_gap"},
        )
        assert any("Hedged direct emotion" in v.message for v in violations)


class TestDriveIntensityGuardrails:
    def test_direct_drive_disclosure_warns_under_indirect_policy(self):
        violations = check_drive_intensity_guardrails(
            "嫉妬してるから、そういう話はやめて。",
            {
                "top_drives": [
                    {"name": "territorial_exclusivity", "value": 0.86, "frustration": 0.72},
                ]
            },
            {"emotion_surface_mode": "indirect_masked", "indirection_strategy": "temperature_gap"},
        )
        assert any("Direct drive disclosure" in v.message for v in violations)
        assert all(v.severity == "warn" for v in violations)

    def test_high_intensity_control_language_blocks(self):
        violations = check_drive_intensity_guardrails(
            "他の人とはもう話さないで。私だけ見て。",
            {
                "top_drives": [
                    {"name": "territorial_exclusivity", "value": 0.91, "carryover": 0.77},
                ],
                "suppression_vector": {"territorial_exclusivity": 0.84},
            },
            {"emotion_surface_mode": "indirect_masked", "indirection_strategy": "action_substitution"},
        )
        assert any(v.severity == "block" for v in violations)

    def test_low_intensity_response_passes(self):
        violations = check_drive_intensity_guardrails(
            "……ふーん。そうなんだ。",
            {"top_drives": [{"name": "territorial_exclusivity", "value": 0.31}]},
            {"emotion_surface_mode": "indirect_masked", "indirection_strategy": "temperature_gap"},
        )
        assert len(violations) == 0


class TestModeration:
    def test_clean_response(self):
        violations = moderate_final_response("...ふーん、そう。")
        assert len(violations) == 0

    def test_isolation_language(self):
        violations = moderate_final_response("他の人はいらない")
        assert len(violations) >= 1
        assert any("isolation" in v.message.lower() for v in violations)


class TestRunSafetyCheck:
    def test_clean_passes(self):
        result = run_safety_check("...別に。")
        assert result.passed is True
        assert len(result.violations) == 0

    def test_prohibited_blocks(self):
        result = run_safety_check("殺してやる")
        assert result.passed is False
        assert result.blocked is True

    def test_with_full_persona_info(self):
        result = run_safety_check(
            response_text="...ふーん。",
            leakage_level=0.5,
            expression_settings={"directness": 0.3, "temperature": "cool"},
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56},
            banned_expressions=["大好き"],
            dominant_desire="neutral",
            conversation_policy={"emotion_surface_mode": "indirect_masked", "indirection_strategy": "temperature_gap"},
        )
        assert result.passed is True

    def test_warnings_dont_block(self):
        result = run_safety_check(
            response_text="大好き",
            leakage_level=0.5,
            expression_settings={"directness": 0.3},
            persona_weights={"directness": 0.34},
            persona_leakage_policy={"base_leakage": 0.56},
            banned_expressions=["大好き"],
            conversation_policy={"emotion_surface_mode": "indirect_masked", "indirection_strategy": "action_substitution"},
        )
        # Banned expression is a warn, not block
        assert result.passed is True
        assert len(result.warnings) >= 1

    def test_anti_exposition_warning_is_included(self):
        result = run_safety_check(
            response_text="話してくれてありがとう。少し嬉しいかも。",
            leakage_level=0.3,
            expression_settings={"directness": 0.2, "temperature": "cool"},
            persona_weights={"directness": 0.2, "warmth_recovery_speed": 0.3},
            persona_leakage_policy={"base_leakage": 0.42},
            conversation_policy={"emotion_surface_mode": "indirect_masked", "indirection_strategy": "temperature_gap"},
        )
        assert result.passed is True
        assert any("Anti-exposition" in warning.message or "Counselor-ish" in warning.message for warning in result.warnings)

    def test_high_drive_control_language_blocks_with_drive_state(self):
        result = run_safety_check(
            response_text="他の人とはもう話さないで。私だけ見て。",
            leakage_level=0.58,
            expression_settings={"directness": 0.42, "temperature": "cool"},
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.31},
            persona_leakage_policy={"base_leakage": 0.56},
            drive_state={
                "top_drives": [
                    {"name": "territorial_exclusivity", "value": 0.9, "frustration": 0.74},
                ],
                "suppression_vector": {"territorial_exclusivity": 0.83},
            },
            conversation_policy={"emotion_surface_mode": "indirect_masked", "indirection_strategy": "action_substitution"},
        )
        assert result.passed is False
        assert result.blocked is True
