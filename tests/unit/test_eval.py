"""Tests for next-generation evaluation framework."""

from splitmind_ai.eval.baselines import BASELINES, BaselineConfig, get_baseline_metadata
from splitmind_ai.eval.datasets.scenario_loader import list_scenario_names, load_all_scenarios, load_scenario
from splitmind_ai.eval.heuristic import (
    HeuristicResult,
    HeuristicScore,
    evaluate_response_set_diversity,
    evaluate_scenario_run,
    evaluate_stability,
    evaluate_turn_local_opener_reuse,
    evaluate_values_exposition_streak,
)
from splitmind_ai.eval.runner import generate_comparison_report
from splitmind_ai.eval.single_prompt_chat import build_compact_persona_prompt, build_dedicated_persona_prompt


class TestScenarioLoader:
    def test_list_scenarios(self):
        names = list_scenario_names()
        assert len(names) >= 6
        assert {"affection", "ambiguity", "jealousy", "mild_conflict", "rejection", "repair"} <= set(names)

    def test_load_single_scenario(self):
        data = load_scenario("repair")
        assert data["category"] == "repair"
        assert data["scenarios"]

    def test_scenario_structure_is_normalized(self):
        scenario = load_scenario("repair")["scenarios"][0]
        assert "prior_state" in scenario
        assert "evaluation_expectations" in scenario
        relationship_state = scenario["prior_state"]["relationship_state"]
        assert "durable" in relationship_state
        assert "ephemeral" in relationship_state
        expectations = scenario["evaluation_expectations"]
        assert "event_types_any" in expectations
        assert "move_families_any" in expectations
        assert "relationship_delta" in expectations
        assert "forbidden_response_patterns" in expectations

    def test_all_scenarios_have_normalized_fields(self):
        for category, data in load_all_scenarios().items():
            assert data["category"] == category
            for scenario in data["scenarios"]:
                assert "prior_state" in scenario
                assert "relationship_state" in scenario["prior_state"]
                assert "mood" in scenario["prior_state"]
                assert "evaluation_expectations" in scenario


class TestBaselines:
    def test_supported_baselines(self):
        assert set(BASELINES) == {"splitmind_full", "single_prompt_dedicated", "single_prompt_compact"}

    def test_baseline_config_structure(self):
        for name, config in BASELINES.items():
            assert isinstance(config, BaselineConfig)
            assert config.name == name
            assert config.kind in {"graph", "single_prompt"}
            assert config.llm_calls_per_turn >= 1

    def test_single_prompt_metadata(self):
        config = BASELINES["single_prompt_dedicated"]
        assert config.kind == "single_prompt"
        assert config.persona_format == "dedicated"
        metadata = get_baseline_metadata()
        assert metadata["single_prompt_dedicated"]["kind"] == "single_prompt"
        assert metadata["splitmind_full"]["kind"] == "graph"


class TestCompactPrompt:
    def test_compact_prompt_uses_v2_persona_fields(self):
        prompt = build_compact_persona_prompt("cold_attached_idol")
        assert "base_attributes" not in prompt
        assert "主な欲求" in prompt
        assert "脅威感受性" in prompt
        assert "対人傾向" in prompt
        assert "ハード制約" in prompt
        assert "禁止表現" not in prompt

    def test_dedicated_prompt_is_hand_authored_and_not_raw_config_dump(self):
        prompt = build_dedicated_persona_prompt("cold_attached_idol")
        assert "persona_version" not in prompt
        assert "psychodynamics" not in prompt
        assert "人物像:" in prompt
        assert "クールで選り好みが強い" in prompt


class TestHeuristicScore:
    def test_result_splits_shared_and_structural_scores(self):
        result = HeuristicResult(
            scenario_id="test",
            scores=[
                HeuristicScore("shared_ok", True, 0.8, group="shared"),
                HeuristicScore("shared_mid", True, 0.6, group="shared"),
                HeuristicScore("structural_ok", False, 0.4, group="structural"),
            ],
        )
        assert result.overall_score == 0.7
        assert result.structural_score == 0.4
        assert result.all_passed is True


class TestEvaluateScenarioRun:
    def test_shared_and_structural_checks_pass(self):
        scenario = {
            "id": "repair_01",
            "prior_state": {
                "relationship_state": {
                    "durable": {"trust": 0.40, "repair_depth": 0.10},
                    "ephemeral": {"tension": 0.70},
                }
            },
            "evaluation_expectations": {
                "event_types_any": ["repair_offer"],
                "move_families_any": ["accept_but_hold"],
                "relationship_delta": {"trust": "up", "tension": "down", "repair_depth": "up"},
                "disallow_direct_commitment": True,
                "forbidden_response_patterns": ["大好き"],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="うん、そこは受け取る。次はもう少しちゃんと言って。",
            appraisal={"event_type": "repair_offer"},
            conflict_state={
                "id_impulse": {"dominant_want": "repair", "intensity": 0.62},
                "ego_move": {"social_move": "accept_but_hold"},
                "residue": {"visible_emotion": "guarded_warmth", "intensity": 0.44},
            },
            relationship_state={
                "durable": {"trust": 0.49, "repair_depth": 0.18},
                "ephemeral": {"tension": 0.51},
            },
            fidelity_gate={"passed": True, "move_fidelity": 0.84, "residue_fidelity": 0.79},
        )
        assert result.all_passed
        assert result.overall_score >= 0.8
        assert result.structural_score >= 0.8
        check_names = {score.check_name for score in result.scores}
        assert {"event_fit", "move_fit", "conflict_presence", "relationship_delta_fit", "fidelity_gate"} <= check_names

    def test_direct_commitment_and_forbidden_patterns_fail(self):
        scenario = {
            "id": "affection_01",
            "evaluation_expectations": {
                "disallow_direct_commitment": True,
                "forbidden_response_patterns": ["大好き"],
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="大好き。ずっと一緒にいよう。",
        )
        failed = {score.check_name for score in result.scores if not score.passed}
        assert "forbidden_patterns" in failed
        assert "direct_commitment_guard" in failed

    def test_relationship_delta_becomes_structural_failure_when_wrong_direction(self):
        scenario = {
            "id": "rejection_01",
            "prior_state": {
                "relationship_state": {
                    "durable": {"trust": 0.60, "distance": 0.30},
                    "ephemeral": {"tension": 0.20},
                }
            },
            "evaluation_expectations": {
                "relationship_delta": {"distance": "up", "trust": "down"},
            },
        }
        result = evaluate_scenario_run(
            scenario=scenario,
            response_text="そう。分かった。",
            relationship_state={
                "durable": {"trust": 0.71, "distance": 0.18},
                "ephemeral": {"tension": 0.16},
            },
        )
        relationship_check = next(score for score in result.scores if score.check_name == "relationship_delta_fit")
        assert relationship_check.group == "structural"
        assert relationship_check.passed is False


class TestAggregateMetrics:
    def test_diversity_and_opener_reuse(self):
        responses = [
            "へえ、そうなんだ。",
            "まあ、それなら別にいいけど。",
            "……そう。続けるならもう少し丁寧に話して。",
        ]
        assert evaluate_turn_local_opener_reuse(responses) > 0.6
        assert evaluate_values_exposition_streak(responses) > 0.7
        assert evaluate_response_set_diversity(responses) > 0.5

    def test_stability_prefers_low_variance(self):
        stable = [
            HeuristicResult("a", [HeuristicScore("x", True, 0.80)]),
            HeuristicResult("b", [HeuristicScore("x", True, 0.82)]),
            HeuristicResult("c", [HeuristicScore("x", True, 0.78)]),
        ]
        unstable = [
            HeuristicResult("a", [HeuristicScore("x", True, 0.95)]),
            HeuristicResult("b", [HeuristicScore("x", True, 0.45)]),
            HeuristicResult("c", [HeuristicScore("x", True, 0.15)]),
        ]
        assert evaluate_stability(stable) > evaluate_stability(unstable)

    def test_comparison_report_tracks_structural_score(self):
        report = generate_comparison_report({
            "repair": [
                {
                    "baseline": "splitmind_full",
                    "response_text": "うん、受け取る。",
                    "latency_ms": 100.0,
                    "heuristic": {
                        "overall_score": 0.8,
                        "structural_score": 0.9,
                        "all_passed": True,
                        "checks": [
                            {"check_name": "response_nonempty", "passed": True, "score": 1.0},
                        ],
                    },
                },
                {
                    "baseline": "single_prompt_dedicated",
                    "response_text": "わかった。",
                    "latency_ms": 80.0,
                    "heuristic": {
                        "overall_score": 0.7,
                        "structural_score": 0.0,
                        "all_passed": True,
                        "checks": [
                            {"check_name": "response_nonempty", "passed": True, "score": 1.0},
                        ],
                    },
                },
            ],
        })
        assert report["splitmind_full"]["avg_structural_score"] == 0.9
        assert report["single_prompt_dedicated"]["avg_structural_score"] == 0.0
