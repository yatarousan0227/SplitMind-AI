"""Load persona definitions from YAML config files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from splitmind_ai.app.settings import PROJECT_ROOT
from splitmind_ai.contracts.persona import PersonaProfile


class PersonaConfig:
    """Parsed persona configuration backed by the v2 persona schema."""

    def __init__(self, data: dict[str, Any], *, name: str) -> None:
        self._model = PersonaProfile.model_validate(data)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def psychodynamics(self) -> dict[str, Any]:
        return self._model.psychodynamics.model_dump(mode="json")

    @property
    def gender(self) -> str:
        return self._model.gender

    @property
    def identity(self) -> dict[str, Any]:
        return self._model.identity.model_dump(mode="json")

    @property
    def relational_profile(self) -> dict[str, Any]:
        return self._model.relational_profile.model_dump(mode="json")

    @property
    def defense_organization(self) -> dict[str, Any]:
        return self._model.defense_organization.model_dump(mode="json")

    @property
    def ego_organization(self) -> dict[str, Any]:
        return self._model.ego_organization.model_dump(mode="json")

    @property
    def safety_boundary(self) -> dict[str, Any]:
        return self._model.safety_boundary.model_dump(mode="json")

    @property
    def relational_policy(self) -> dict[str, Any]:
        return self._model.relational_policy.model_dump(mode="json")

    def to_slice(self) -> dict[str, Any]:
        """Convert to PersonaSlice dict for the agent state."""
        return self._model.model_dump(mode="json")

    @property
    def raw(self) -> dict[str, Any]:
        return self._model.model_dump(mode="json")


def load_persona(persona_name: str, directory: str | Path | None = None) -> PersonaConfig:
    """Load a persona YAML file by name."""
    if directory is None:
        directory = PROJECT_ROOT / "configs" / "personas"
    else:
        directory = Path(directory)

    path = directory / f"{persona_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona config not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return PersonaConfig(data, name=path.stem)


def list_personas(directory: str | Path | None = None) -> list[str]:
    """List available persona names."""
    if directory is None:
        directory = PROJECT_ROOT / "configs" / "personas"
    else:
        directory = Path(directory)

    if not directory.exists():
        return []

    return [p.stem for p in sorted(directory.glob("*.yaml"))]
