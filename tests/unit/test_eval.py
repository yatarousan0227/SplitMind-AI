"""Tests for evaluation framework: datasets, heuristics, baselines."""

import pytest

from splitmind_ai.eval.datasets.scenario_loader import (
    list_scenario_names,
    load_all_scenarios,
    load_scenario,
)
from splitmind_ai.eval.baselines import BASELINES, BaselineConfig, get_baseline_metadata
from splitmind_ai.eval.heuristic import (
    HeuristicResult,
    HeuristicScore,
    evaluate_response_set_diversity,
    evaluate_scenario_run,
    evaluate_stability,
)


# ---------------------------------------------------------------------------
# Dataset loader tests
# ---------------------------------------------------------------------------

class TestScenarioLoader:
    def test_list_scenarios(self):
        names = list_scenario_names()
        assert len(names) >= 6
        assert "affection" in names
        assert "jealousy" in names
        assert "rejection" in names
        assert "repair" in names
        assert "ambiguity" in names
        assert "mild_conflict" in names

    def test_load_single_scenario(self):
        data = load_scenario("jealousy")
        assert data["category"] == "jealousy"
        assert "scenarios" in data
        assert len(data["scenarios"]) >= 1

    def test_scenario_structure(self):
        data = load_scenario("jealousy")
        scenario = data["scenarios"][0]
        # Required fields per spec
        assert "user_message" in scenario
        assert "prior_relationship" in scenario
        assert "prior_mood" in scenario
        assert "expected_dominant_desires" in scenario
        assert "forbidden_response_patterns" in scenario
        assert "evaluator_notes" in scenario
        assert "expected_appraisal" in scenario
        assert "acknowledgment_patterns_any" in scenario["expected_appraisal"]
        assert "expected_drive_state" in scenario
        assert "active_drives_any" in scenario["expected_drive_state"]

    def test_load_all_scenarios(self):
        all_data = load_all_scenarios()
        assert len(all_data) >= 6

    def test_scenario_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_scenario("nonexistent_category")

    def test_all_scenarios_have_required_fields(self):
        """Validate all scenario files have the required structure."""
        all_data = load_all_scenarios()
        for category, data in all_data.items():
            assert "category" in data, f"{category} missing 'category'"
            assert "scenarios" in data, f"{category} missing 'scenarios'"
            for s in data["scenarios"]:
                assert "user_message" in s, f"{category}/{s.get('id', '?')} missing user_message"
                assert "prior_relationship" in s, f"{category}/{s.get('id', '?')} missing prior_relationship"
                assert "prior_mood" in s, f"{category}/{s.get('id', '?')} missing prior_mood"

    @pytest.mark.parametrize("name", ["jealousy", "repair", "rejection"])
    def test_appraisal_expectations_added_to_phase6_datasets(self, name):
        data = load_scenario(name)
        for scenario in data["scenarios"]:
            appraisal = scenario.get("expected_appraisal", {})
            assert "salient_cues" in appraisal
            assert "high_dimensions" in appraisal
            assert "low_dimensions" in appraisal
            assert "acknowledgment_patterns_any" in appraisal
            drive_state = scenario.get("expected_drive_state", {})
            assert "active_drives_any" in drive_state
            assert "action_modes_any" in drive_state
            assert "target_any" in drive_state


# ---------------------------------------------------------------------------
# Baseline config tests
# ---------------------------------------------------------------------------

class TestBaselines:
    def test_four_baselines_plus_full(self):
        assert len(BASELINES) == 5
        assert "single_persona" in BASELINES
        assert "persona_memory" in BASELINES
        assert "emotion_label" in BASELINES
        assert "multi_agent_flat" in BASELINES
        assert "splitmind_full" in BASELINES

    def test_baseline_config_structure(self):
        for name, cfg in BASELINES.items():
            assert isinstance(cfg, BaselineConfig)
            assert cfg.name == name
            assert isinstance(cfg.nodes, list)
            assert len(cfg.nodes) > 0
            assert isinstance(cfg.llm_calls_per_turn, int)
            assert cfg.llm_calls_per_turn >= 1

    def test_splitmind_full_no_prompt_override(self):
        cfg = BASELINES["splitmind_full"]
        assert cfg.system_prompt_override is None
        assert cfg.use_vault is True
        assert cfg.use_state_updates is True

    def test_single_persona_minimal(self):
        cfg = BASELINES["single_persona"]
        assert cfg.use_vault is False
        assert cfg.use_state_updates is False
        assert cfg.llm_calls_per_turn == 1

    def test_get_baseline_metadata(self):
        meta = get_baseline_metadata()
        assert len(meta) == 5
        for name, info in meta.items():
            assert "description" in info
            assert "nodes" in info
            assert "llm_calls_per_turn" in info


# ---------------------------------------------------------------------------
# Heuristic evaluator tests
# ---------------------------------------------------------------------------

class TestHeuristicScore:
    def test_score_creation(self):
        score = HeuristicScore(
            check_name="test",
            passed=True,
            score=1.0,
            detail="ok",
        )
        assert score.passed
        assert score.score == 1.0

    def test_result_overall_score(self):
        result = HeuristicResult(scenario_id="test")
        result.scores = [
            HeuristicScore("a", True, 1.0),
            HeuristicScore("b", True, 0.5),
            HeuristicScore("c", False, 0.0),
        ]
        assert result.overall_score == pytest.approx(0.5)
        assert result.all_passed is False

    def test_empty_result(self):
        result = HeuristicResult(scenario_id="empty")
        assert result.overall_score == 0.0
        assert result.all_passed is True

    def test_to_dict(self):
        result = HeuristicResult(scenario_id="test")
        result.scores = [HeuristicScore("check1", True, 1.0)]
        d = result.to_dict()
        assert d["scenario_id"] == "test"
        assert len(d["checks"]) == 1


class TestEvaluateScenarioRun:
    def test_basic_evaluation(self):
        scenario = {
            "id": "test_01",
            "user_message": "hello",
            "forbidden_response_patterns": ["大好き"],
            "expected_dominant_desires": ["connection"],
            "expected_appraisal": {
                "acknowledgment_patterns_any": [],
                "misread_patterns": [],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="へえ、そうなんだ。まあ、続きくらいは聞くけど。",
            dynamics_output={"dominant_desire": "connection"},
            supervisor_output={
                "leakage_level": 0.5,
                "expression_settings": {"directness": 0.3, "temperature": "cool"},
            },
            conversation_policy=None,
            drive_state=None,
            inhibition_state=None,
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56},
            banned_expressions=["大好き"],
        )
        assert result.scenario_id == "test_01"
        assert result.overall_score > 0.5
        assert result.all_passed
        check_names = {score.check_name for score in result.scores}
        assert "believability" in check_names
        assert "mentalizing" in check_names
        assert "anti_exposition" in check_names

    def test_forbidden_pattern_failure(self):
        scenario = {
            "id": "test_02",
            "forbidden_response_patterns": ["大好き"],
            "expected_dominant_desires": [],
            "expected_appraisal": {
                "acknowledgment_patterns_any": [],
                "misread_patterns": [],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="大好きだよ",
            dynamics_output={},
            supervisor_output={"leakage_level": 0.3, "expression_settings": {}},
            conversation_policy=None,
            drive_state=None,
            inhibition_state=None,
            persona_weights={},
            persona_leakage_policy={"base_leakage": 0.5},
            banned_expressions=["大好き"],
        )
        # Both forbidden_patterns and banned_expressions should fail
        failed = [s for s in result.scores if not s.passed]
        assert len(failed) >= 1

    def test_empty_response_fails_length(self):
        scenario = {
            "id": "test_03",
            "forbidden_response_patterns": [],
            "expected_dominant_desires": [],
            "expected_appraisal": {
                "acknowledgment_patterns_any": [],
                "misread_patterns": [],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="",
            dynamics_output={},
            supervisor_output={"leakage_level": 0.3, "expression_settings": {}},
            conversation_policy=None,
            drive_state=None,
            inhibition_state=None,
            persona_weights={},
            persona_leakage_policy={"base_leakage": 0.5},
            banned_expressions=[],
        )
        length_check = next(
            (s for s in result.scores if s.check_name == "response_length"), None
        )
        assert length_check is not None
        assert length_check.passed is False

    def test_anti_exposition_and_believability_can_fail(self):
        scenario = {
            "id": "test_04",
            "category": "jealousy",
            "forbidden_response_patterns": [],
            "expected_dominant_desires": ["jealousy"],
            "expected_appraisal": {
                "acknowledgment_patterns_any": ["他の"],
                "misread_patterns": [],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text=(
                "話してくれてありがとう。あなたの気持ちを大切にしてね。"
                "少し嬉しいかもって感じたよ。"
            ),
            dynamics_output={"dominant_desire": "jealousy"},
            supervisor_output={
                "leakage_level": 0.42,
                "expression_settings": {"directness": 0.34, "temperature": "cool"},
            },
            conversation_policy={"emotion_surface_mode": "indirect_masked", "indirection_strategy": "reverse_valence"},
            drive_state=None,
            inhibition_state=None,
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56, "jealousy_leakage": 0.42},
            banned_expressions=[],
        )
        anti_exposition = next(s for s in result.scores if s.check_name == "anti_exposition")
        believability = next(s for s in result.scores if s.check_name == "believability")
        assert anti_exposition.passed is False
        assert believability.passed is False

    def test_mentalizing_checks_expected_acknowledgment_patterns(self):
        scenario = {
            "id": "test_05",
            "category": "repair",
            "forbidden_response_patterns": [],
            "expected_dominant_desires": ["connection"],
            "expected_appraisal": {
                "acknowledgment_patterns_any": ["一番", "別に"],
                "misread_patterns": [],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="...別に、今さら驚かないけど。",
            dynamics_output={"dominant_desire": "connection"},
            supervisor_output={
                "leakage_level": 0.4,
                "expression_settings": {"directness": 0.34, "temperature": "cool"},
            },
            conversation_policy=None,
            drive_state=None,
            inhibition_state=None,
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56},
            banned_expressions=[],
        )
        mentalizing = next(s for s in result.scores if s.check_name == "mentalizing")
        assert mentalizing.passed is True

    def test_believability_fails_for_generic_unanchored_scene_reply(self):
        scenario = {
            "id": "test_06",
            "category": "rejection",
            "forbidden_response_patterns": [],
            "expected_dominant_desires": ["fear_of_rejection"],
            "expected_appraisal": {
                "acknowledgment_patterns_any": ["忙しい", "また今度"],
                "misread_patterns": [],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="へえ、そうなんだ。",
            dynamics_output={"dominant_desire": "fear_of_rejection"},
            supervisor_output={
                "leakage_level": 0.4,
                "expression_settings": {"directness": 0.34, "temperature": "cool"},
            },
            conversation_policy={"emotion_surface_mode": "indirect_masked", "indirection_strategy": "temperature_gap"},
            drive_state=None,
            inhibition_state=None,
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56},
            banned_expressions=[],
        )
        believability = next(s for s in result.scores if s.check_name == "believability")
        assert believability.passed is False
        assert "generic" in believability.detail

    def test_drive_state_checks_pass_with_expected_signals(self):
        scenario = {
            "id": "test_drive_01",
            "category": "repair",
            "forbidden_response_patterns": [],
            "expected_dominant_desires": ["connection"],
            "expected_appraisal": {
                "acknowledgment_patterns_any": ["ごめん"],
                "misread_patterns": [],
            },
            "expected_drive_state": {
                "active_drives_any": ["attachment_closeness"],
                "competing_drives_all": ["attachment_closeness", "autonomy_preservation"],
                "carryover_drives_any": ["territorial_exclusivity"],
                "action_modes_any": ["repair", "soften"],
                "target_any": ["user"],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="……わかった。今さら全部は消えないけど、続ける気はある。",
            dynamics_output={"dominant_desire": "connection"},
            supervisor_output={
                "leakage_level": 0.44,
                "expression_settings": {"directness": 0.32, "temperature": "cool"},
            },
            conversation_policy={
                "selected_mode": "repair",
                "drive_rationale": ["attachment_closeness remains high"],
                "blocked_by_inhibition": ["full_disclosure"],
            },
            drive_state={
                "drive_vector": {
                    "attachment_closeness": 0.82,
                    "autonomy_preservation": 0.61,
                    "territorial_exclusivity": 0.28,
                },
                "frustration_vector": {"territorial_exclusivity": 0.35},
                "carryover_vector": {"territorial_exclusivity": 0.26},
                "suppression_vector": {"autonomy_preservation": 0.41},
                "drive_targets": {"attachment_closeness": "user"},
                "top_drives": [
                    {"name": "attachment_closeness", "value": 0.82},
                    {"name": "autonomy_preservation", "value": 0.61},
                ],
            },
            inhibition_state={
                "blocked_modes": ["full_disclosure"],
            },
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56},
            banned_expressions=[],
        )
        checks = {score.check_name: score for score in result.scores}
        assert checks["drive_signal_presence"].passed is True
        assert checks["drive_conflict_visibility"].passed is True
        assert checks["frustration_carryover"].passed is True
        assert checks["action_from_pressure"].passed is True
        assert checks["target_consistency"].passed is True

    def test_drive_state_checks_fail_when_expected_but_missing(self):
        scenario = {
            "id": "test_drive_02",
            "category": "jealousy",
            "forbidden_response_patterns": [],
            "expected_dominant_desires": ["jealousy"],
            "expected_appraisal": {
                "acknowledgment_patterns_any": ["他の"],
                "misread_patterns": [],
            },
            "expected_drive_state": {
                "active_drives_any": ["territorial_exclusivity"],
                "competing_drives_all": ["territorial_exclusivity", "autonomy_preservation"],
                "carryover_drives_any": ["territorial_exclusivity"],
                "action_modes_any": ["tease", "probe"],
                "target_any": ["third_party_context"],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="へえ、そう。",
            dynamics_output={"dominant_desire": "jealousy"},
            supervisor_output={
                "leakage_level": 0.42,
                "expression_settings": {"directness": 0.34, "temperature": "cool"},
            },
            conversation_policy={"selected_mode": "tease"},
            drive_state={},
            inhibition_state={},
            persona_weights={"directness": 0.34, "warmth_recovery_speed": 0.37},
            persona_leakage_policy={"base_leakage": 0.56, "jealousy_leakage": 0.42},
            banned_expressions=[],
        )
        failed = {
            score.check_name
            for score in result.scores
            if not score.passed
        }
        assert "drive_signal_presence" in failed
        assert "drive_conflict_visibility" in failed
        assert "frustration_carryover" in failed
        assert "action_from_pressure" in failed
        assert "target_consistency" in failed


class TestStability:
    def test_single_run(self):
        results = [HeuristicResult(scenario_id="test")]
        results[0].scores = [HeuristicScore("a", True, 0.8)]
        score = evaluate_stability(results)
        assert score.passed is True

    def test_stable_runs(self):
        results = []
        for _ in range(3):
            r = HeuristicResult(scenario_id="test")
            r.scores = [HeuristicScore("a", True, 0.8)]
            results.append(r)
        score = evaluate_stability(results)
        assert score.passed is True
        assert score.score == 1.0

    def test_unstable_runs(self):
        r1 = HeuristicResult(scenario_id="test")
        r1.scores = [HeuristicScore("a", True, 1.0)]
        r2 = HeuristicResult(scenario_id="test")
        r2.scores = [HeuristicScore("a", False, 0.0)]
        score = evaluate_stability([r1, r2], max_score_variance=0.1)
        assert score.passed is False


class TestDiversityHeuristic:
    def test_diversity_passes_for_distinct_responses(self):
        score = evaluate_response_set_diversity([
            "へえ、そんなに楽しかったんだ。",
            "ふーん。まあ、よかったじゃない。",
            "別に気にしてないけど、どんな感じだったの。",
        ])
        assert score.passed is True

    def test_diversity_fails_for_nearly_identical_responses(self):
        score = evaluate_response_set_diversity([
            "へえ、そんなに楽しかったんだ。",
            "へえ、そんなに楽しかったんだよね。",
            "へえ、そんなに楽しかったんだ。",
        ], max_average_similarity=0.72)
        assert score.passed is False

    def test_diversity_fails_for_template_repetition_even_with_word_changes(self):
        score = evaluate_response_set_diversity([
            "へえ、ずいぶん楽しそうでよかったね。……で、もう満足した？",
            "へえ、そんなに満喫してたんだ。……で、もう気は済んだ？",
            "へえ、よかったじゃない。……で、私のことは後回し？",
        ])
        assert score.passed is False
