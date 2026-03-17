"""Application settings loaded from agent_config.yaml and environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


def _project_root() -> Path:
    """Walk up from this file to find the project root (where pyproject.toml lives)."""
    cur = Path(__file__).resolve().parent
    for _ in range(10):
        if (cur / "pyproject.toml").exists():
            return cur
        cur = cur.parent
    return Path.cwd()


PROJECT_ROOT = _project_root()


def load_project_dotenv(dotenv_path: Path | None = None) -> Path | None:
    """Load a .env file so SDKs that read os.environ can see credentials."""
    candidates = [dotenv_path] if dotenv_path else [Path.cwd() / ".env", PROJECT_ROOT / ".env"]
    seen: set[Path] = set()

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        load_dotenv(resolved, override=False)
        return resolved

    return None


class LLMSettings(BaseModel):
    provider: Literal["azure", "openai"] = "azure"
    model: str = "gpt-4.1"
    azure_deployment: str = "gpt-4.1"
    api_version: str = "2024-12-01-preview"
    temperature: float | None = None
    max_tokens: int | None = None


class RuntimeSettings(BaseModel):
    max_iterations: int = 10
    supervisor: str = "main"


class VaultSettings(BaseModel):
    path: str = "./vault"
    enabled: bool = True


class MoodSettings(BaseModel):
    decay_rate: float = 0.1
    decay_turns: int = 3


class PersonasSettings(BaseModel):
    default: str = "cold_attached_idol"
    directory: str = "configs/personas"


class StateUpdateRule(BaseModel):
    trust: float = 0.0
    intimacy: float = 0.0
    distance: float = 0.0
    tension: float = 0.0
    attachment_pull: float = 0.0


class Settings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    vault: VaultSettings = Field(default_factory=VaultSettings)
    mood: MoodSettings = Field(default_factory=MoodSettings)
    personas: PersonasSettings = Field(default_factory=PersonasSettings)
    state_update_rules: dict[str, StateUpdateRule] = Field(default_factory=dict)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _llm_provider(raw: str) -> Literal["azure", "openai"]:
    provider = raw.strip().lower()
    if provider not in {"azure", "openai"}:
        raise ValueError("SPLITMIND_LLM_PROVIDER must be either 'azure' or 'openai'")
    return provider


def _apply_env_overrides(settings: Settings) -> Settings:
    settings.llm.provider = _llm_provider(
        os.environ.get("SPLITMIND_LLM_PROVIDER", settings.llm.provider)
    )
    settings.llm.model = os.environ.get(
        "SPLITMIND_LLM_MODEL",
        os.environ.get("OPENAI_MODEL", settings.llm.model),
    )
    settings.llm.azure_deployment = os.environ.get(
        "AZURE_OPENAI_DEPLOYMENT",
        settings.llm.azure_deployment,
    )
    settings.llm.api_version = os.environ.get(
        "AZURE_OPENAI_API_VERSION",
        settings.llm.api_version,
    )
    settings.vault.path = os.environ.get("SPLITMIND_VAULT_PATH", settings.vault.path)
    settings.vault.enabled = _env_flag("SPLITMIND_VAULT_ENABLED", settings.vault.enabled)
    settings.personas.default = os.environ.get("SPLITMIND_PERSONA", settings.personas.default)
    return settings


def load_settings(
    config_path: Path | None = None,
    dotenv_path: Path | None = None,
) -> Settings:
    """Load settings from YAML config file."""
    load_project_dotenv(dotenv_path)

    if config_path is None:
        config_path = PROJECT_ROOT / "configs" / "agent_config.yaml"

    if not config_path.exists():
        return _apply_env_overrides(Settings())

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    rules_raw = raw.pop("state_update", {}).get("rules", {})
    rules = {k: StateUpdateRule(**v) for k, v in rules_raw.items()}

    settings = Settings(
        **{k: v for k, v in raw.items() if k != "state_update"},
        state_update_rules=rules,
    )
    return _apply_env_overrides(settings)


# Convenience: override persona from env
def get_default_persona(settings: Settings) -> str:
    return os.environ.get("SPLITMIND_PERSONA", settings.personas.default)
