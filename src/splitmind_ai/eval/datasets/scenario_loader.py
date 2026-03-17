"""Load evaluation scenario YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DATASETS_DIR = Path(__file__).parent


def load_scenario(name: str) -> dict[str, Any]:
    """Load a single scenario YAML by name (without extension)."""
    path = DATASETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def load_all_scenarios() -> dict[str, dict[str, Any]]:
    """Load all scenario YAML files in the datasets directory."""
    scenarios: dict[str, dict[str, Any]] = {}
    for path in sorted(DATASETS_DIR.glob("*.yaml")):
        with open(path) as f:
            scenarios[path.stem] = yaml.safe_load(f)
    return scenarios


def list_scenario_names() -> list[str]:
    """List available scenario names (file stems)."""
    return [p.stem for p in sorted(DATASETS_DIR.glob("*.yaml"))]
