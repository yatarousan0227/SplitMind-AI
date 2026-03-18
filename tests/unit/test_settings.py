"""Tests for settings and environment loading."""

from pathlib import Path

from splitmind_ai.app.settings import load_settings


def test_load_settings_reads_dotenv_and_applies_env_overrides(tmp_path, monkeypatch):
    config_path = tmp_path / "agent_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "llm:",
                "  provider: azure",
                "  model: yaml-model",
                "  azure_deployment: yaml-deployment",
                '  api_version: "2024-01-01-preview"',
                "memory_store:",
                "  path: ./memory-from-yaml",
                "  enabled: true",
                "personas:",
                "  default: yaml-persona",
            ]
        ),
        encoding="utf-8",
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "SPLITMIND_LLM_PROVIDER=openai",
                "SPLITMIND_LLM_MODEL=gpt-4.1-mini",
                "AZURE_OPENAI_API_KEY=test-key",
                "AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/",
                "AZURE_OPENAI_DEPLOYMENT=dotenv-deployment",
                "AZURE_OPENAI_API_VERSION=2024-12-01-preview",
                "SPLITMIND_PERSONA=dotenv-persona",
                "SPLITMIND_MEMORY_STORE_PATH=./memory-from-dotenv",
                "SPLITMIND_MEMORY_STORE_ENABLED=false",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("SPLITMIND_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SPLITMIND_LLM_MODEL", raising=False)
    monkeypatch.delenv("SPLITMIND_PERSONA", raising=False)
    monkeypatch.delenv("SPLITMIND_MEMORY_STORE_PATH", raising=False)
    monkeypatch.delenv("SPLITMIND_MEMORY_STORE_ENABLED", raising=False)
    monkeypatch.delenv("SPLITMIND_VAULT_PATH", raising=False)
    monkeypatch.delenv("SPLITMIND_VAULT_ENABLED", raising=False)

    settings = load_settings(config_path=config_path, dotenv_path=dotenv_path)

    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4.1-mini"
    assert settings.llm.azure_deployment == "dotenv-deployment"
    assert settings.llm.api_version == "2024-12-01-preview"
    assert settings.personas.default == "dotenv-persona"
    assert settings.memory_store.path == "./memory-from-dotenv"
    assert settings.memory_store.enabled is False


def test_load_settings_without_config_still_uses_env(tmp_path, monkeypatch):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "SPLITMIND_LLM_PROVIDER=openai",
                "OPENAI_MODEL=gpt-4.1-nano",
                "AZURE_OPENAI_DEPLOYMENT=env-only-deployment",
                "AZURE_OPENAI_API_VERSION=2025-01-01-preview",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("SPLITMIND_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SPLITMIND_LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)

    settings = load_settings(
        config_path=Path(tmp_path / "missing.yaml"),
        dotenv_path=dotenv_path,
    )

    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4.1-nano"
    assert settings.llm.azure_deployment == "env-only-deployment"
    assert settings.llm.api_version == "2025-01-01-preview"


def test_load_settings_reads_runtime_max_iterations(tmp_path):
    config_path = tmp_path / "agent_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "runtime:",
                "  max_iterations: 14",
                "  supervisor: main",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path=config_path)

    assert settings.runtime.max_iterations == 14
