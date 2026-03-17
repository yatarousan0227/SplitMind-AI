"""Load persona definitions from YAML config files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from splitmind_ai.app.settings import PROJECT_ROOT


class PersonaConfig:
    """Parsed persona configuration."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def name(self) -> str:
        return self._data["persona_name"]

    @property
    def weights(self) -> dict[str, float]:
        return self._data.get("weights", {})

    @property
    def base_attributes(self) -> dict[str, str]:
        return self._data.get("base_attributes", {})

    @property
    def defense_biases(self) -> dict[str, float]:
        return self._data.get("defense_biases", {})

    @property
    def leakage_policy(self) -> dict[str, float]:
        return self._data.get("leakage_policy", {})

    @property
    def tone_guardrails(self) -> list[str]:
        return self._data.get("tone_guardrails", [])

    @property
    def prohibited_expressions(self) -> list[str]:
        return self._data.get("prohibited_expressions", [])

    def to_slice(self) -> dict[str, Any]:
        """Convert to PersonaSlice dict for the agent state."""
        return {
            "persona_name": self.name,
            "weights": self.weights,
            "base_attributes": self.base_attributes,
            "defense_biases": self.defense_biases,
            "leakage_policy": self.leakage_policy,
            "tone_guardrails": self.tone_guardrails,
            "prohibited_expressions": self.prohibited_expressions,
        }

    @property
    def raw(self) -> dict[str, Any]:
        return self._data


def load_persona(persona_name: str, directory: str | Path | None = None) -> PersonaConfig:
    """Load a persona YAML file by name.

    Args:
        persona_name: File stem (without .yaml extension).
        directory: Optional directory path. Defaults to configs/personas/.
    """
    if directory is None:
        directory = PROJECT_ROOT / "configs" / "personas"
    else:
        directory = Path(directory)

    path = directory / f"{persona_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona config not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return PersonaConfig(data)


def list_personas(directory: str | Path | None = None) -> list[str]:
    """List available persona names."""
    if directory is None:
        directory = PROJECT_ROOT / "configs" / "personas"
    else:
        directory = Path(directory)

    if not directory.exists():
        return []

    return [p.stem for p in sorted(directory.glob("*.yaml"))]
