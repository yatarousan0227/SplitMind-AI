"""Tests for prompt building."""

from splitmind_ai.prompts.internal_dynamics import build_internal_dynamics_prompt
from splitmind_ai.prompts.persona_supervisor import (
    build_combined_supervisor_realization_prompt,
    build_persona_supervisor_prompt,
    build_surface_realization_prompt,
)


def test_internal_dynamics_prompt_structure():
    messages = build_internal_dynamics_prompt(
        user_message="今日は他の人とすごく楽しかった",
        conversation_context=[],
        persona={"persona_name": "test", "weights": {}},
        relationship={"trust": 0.5},
        mood={"base_mood": "calm"},
        memory={},
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "イド" in messages[0]["content"]
    assert "自我" in messages[0]["content"]
    assert "超自我" in messages[0]["content"]
    assert "今日は他の人とすごく楽しかった" in messages[1]["content"]


def test_persona_supervisor_prompt_structure():
    messages = build_persona_supervisor_prompt(
        user_message="test",
        persona={"persona_name": "test"},
        relationship={"trust": 0.5},
        mood={"base_mood": "calm"},
        dynamics={"dominant_desire": "jealousy"},
        drive_state={"top_drives": [{"name": "territorial_exclusivity", "value": 0.82}]},
        appraisal={"dominant_appraisal": "competitive"},
        conversation_policy={"selected_mode": "tease"},
        memory={},
        event_flags={"jealousy_trigger": True},
        response_language="en",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "ペルソナ・スーパーバイザー" in messages[0]["content"]
    assert "まとめきれないこともあります" in messages[0]["content"]
    assert "jealousy" in messages[1]["content"]
    assert "Conversation Policy" in messages[1]["content"]
    assert "Drive State" in messages[1]["content"]
    assert "English" in messages[0]["content"]
    assert "## 応答言語\nEnglish" in messages[1]["content"]
    assert "emotion_surface_mode" in messages[0]["content"]
    assert "indirection_strategy" in messages[0]["content"]
    assert "欲求ラベルや drive の名前を本文で自己解説しない" in messages[0]["content"]


def test_surface_realization_prompt_structure():
    messages = build_surface_realization_prompt(
        user_message="test",
        persona={"persona_name": "test"},
        relationship={"trust": 0.5},
        mood={"base_mood": "calm"},
        dynamics={"dominant_desire": "jealousy"},
        drive_state={"top_drives": [{"name": "territorial_exclusivity", "value": 0.82}]},
        appraisal={"dominant_appraisal": "competitive"},
        conversation_policy={"selected_mode": "tease"},
        utterance_plan={
            "surface_intent": "test",
            "expression_settings": {"length": "medium"},
            "candidates": [
                {"label": "a", "mode": "tease", "opening_style": "short", "interpersonal_move": "test", "latent_signal": "sting"},
                {"label": "b", "mode": "probe", "opening_style": "cool", "interpersonal_move": "probe", "latent_signal": "curiosity"},
            ],
        },
        memory={},
        response_language="en",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "surface realization" in messages[0]["content"]
    assert "selected_text" in messages[0]["content"]
    assert "Persona Frame" in messages[1]["content"]
    assert "Length Guidance" in messages[1]["content"]
    assert "English" in messages[0]["content"]
    assert "2-4文" in messages[1]["content"]
    assert "Drive State" in messages[1]["content"]
    assert "emotion_surface_mode" in messages[0]["content"]
    assert "latent drive signature は本文で説明せず" in messages[0]["content"]


def test_combined_supervisor_realization_prompt_structure():
    messages = build_combined_supervisor_realization_prompt(
        user_message="test",
        persona={"persona_name": "test"},
        relationship={"trust": 0.5},
        mood={"base_mood": "calm"},
        dynamics={"dominant_desire": "jealousy"},
        drive_state={"top_drives": [{"name": "territorial_exclusivity", "value": 0.82}]},
        appraisal={"dominant_appraisal": "competitive"},
        conversation_policy={"selected_mode": "tease"},
        memory={},
        event_flags={"jealousy_trigger": True},
        response_language="en",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "統合 supervisor ノード" in messages[0]["content"]
    assert "selected_text" in messages[0]["content"]
    assert "English" in messages[0]["content"]
    assert "Drive State" in messages[1]["content"]
    assert "イベントフラグ" in messages[1]["content"]


def test_dynamics_prompt_includes_schema():
    messages = build_internal_dynamics_prompt(
        user_message="test",
        conversation_context=[],
        persona={},
        relationship={},
        mood={},
        memory={},
    )
    # Schema should be embedded in system prompt
    assert "id_output" in messages[0]["content"]
    assert "ego_output" in messages[0]["content"]
    assert "defense_output" in messages[0]["content"]
