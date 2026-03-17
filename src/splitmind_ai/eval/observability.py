"""Observability utilities: trace export, contract visualization, contract diff.

Leverages agent-contracts for contract visualization and validation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_contracts import get_node_registry

from splitmind_ai.app.graph import register_all_nodes

logger = logging.getLogger(__name__)

TRACES_DIR = Path(__file__).parent / "traces"


# ---------------------------------------------------------------------------
# Trace export
# ---------------------------------------------------------------------------

def save_scenario_trace(
    scenario_id: str,
    baseline: str,
    result: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    """Save a scenario execution trace to JSON.

    Args:
        scenario_id: Scenario identifier.
        baseline: Baseline name.
        result: Full result dict from the evaluation runner.
        output_dir: Directory to save traces. Defaults to eval/traces/.

    Returns:
        Path to the saved trace file.
    """
    output_dir = output_dir or TRACES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{scenario_id}_{baseline}_{timestamp}.json"
    path = output_dir / filename

    trace_data = {
        "scenario_id": scenario_id,
        "baseline": baseline,
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }

    with open(path, "w") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)

    logger.info("Trace saved: %s", path)
    return path


def load_traces(
    scenario_id: str | None = None,
    baseline: str | None = None,
    traces_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Load saved traces, optionally filtered by scenario/baseline."""
    traces_dir = traces_dir or TRACES_DIR
    if not traces_dir.exists():
        return []

    traces: list[dict[str, Any]] = []
    for path in sorted(traces_dir.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if scenario_id and data.get("scenario_id") != scenario_id:
            continue
        if baseline and data.get("baseline") != baseline:
            continue
        traces.append(data)

    return traces


# ---------------------------------------------------------------------------
# Contract visualization
# ---------------------------------------------------------------------------

def generate_contract_docs(output_dir: Path | None = None) -> dict[str, Any]:
    """Generate contract documentation from node registry.

    Returns a dict with node contracts, their reads/writes, triggers,
    and a Mermaid flowchart string.
    """
    from splitmind_ai.app.graph import register_all_nodes

    reset_registry_safe()
    register_all_nodes()
    registry = get_node_registry()

    nodes: list[dict[str, Any]] = []
    for node_name in registry.get_all_nodes():
        contract = registry.get_contract(node_name)
        if contract is None:
            continue
        nodes.append({
            "name": contract.name,
            "description": contract.description,
            "reads": list(contract.reads),
            "writes": list(contract.writes),
            "supervisor": contract.supervisor,
            "is_terminal": contract.is_terminal,
            "icon": getattr(contract, "icon", ""),
            "triggers": [
                {
                    "priority": tc.priority,
                    "when": tc.when,
                    "llm_hint": tc.llm_hint,
                }
                for tc in contract.trigger_conditions
            ],
        })

    # Generate Mermaid flowchart
    mermaid = _generate_mermaid(nodes)

    doc = {
        "generated_at": datetime.now().isoformat(),
        "node_count": len(nodes),
        "nodes": nodes,
        "mermaid": mermaid,
    }

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "contracts.json", "w") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        with open(output_dir / "architecture.mmd", "w") as f:
            f.write(mermaid)
        logger.info("Contract docs saved to %s", output_dir)

    return doc


def _generate_mermaid(nodes: list[dict[str, Any]]) -> str:
    """Generate a Mermaid flowchart from node contracts."""
    lines = ["graph TD"]

    # Sort by trigger priority (highest first = runs first)
    sorted_nodes = sorted(
        nodes,
        key=lambda n: n["triggers"][0]["priority"] if n["triggers"] else 0,
        reverse=True,
    )

    for node in sorted_nodes:
        icon = node.get("icon", "")
        label = f"{icon} {node['name']}" if icon else node["name"]
        terminal = " (terminal)" if node["is_terminal"] else ""
        lines.append(f'    {node["name"]}["{label}{terminal}"]')

    # Add edges based on data dependencies (writes -> reads)
    write_map: dict[str, list[str]] = {}
    for node in sorted_nodes:
        for w in node["writes"]:
            write_map.setdefault(w, []).append(node["name"])

    for node in sorted_nodes:
        for r in node["reads"]:
            for writer in write_map.get(r, []):
                if writer != node["name"]:
                    lines.append(f"    {writer} -->|{r}| {node['name']}")

    return "\n".join(lines)


def reset_registry_safe() -> None:
    """Reset registry, catching import errors gracefully."""
    try:
        from agent_contracts import reset_registry
        reset_registry()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Contract diff
# ---------------------------------------------------------------------------

def diff_contracts(
    old_doc: dict[str, Any],
    new_doc: dict[str, Any],
) -> dict[str, Any]:
    """Compare two contract doc snapshots and return differences.

    Returns a dict with: added_nodes, removed_nodes, changed_nodes.
    """
    old_nodes = {n["name"]: n for n in old_doc.get("nodes", [])}
    new_nodes = {n["name"]: n for n in new_doc.get("nodes", [])}

    added = [n for name, n in new_nodes.items() if name not in old_nodes]
    removed = [n for name, n in old_nodes.items() if name not in new_nodes]

    changed: list[dict[str, Any]] = []
    for name in old_nodes:
        if name in new_nodes:
            old_n = old_nodes[name]
            new_n = new_nodes[name]
            diffs: dict[str, Any] = {}
            for key in ("reads", "writes", "is_terminal", "triggers"):
                if old_n.get(key) != new_n.get(key):
                    diffs[key] = {"old": old_n.get(key), "new": new_n.get(key)}
            if diffs:
                changed.append({"name": name, "changes": diffs})

    return {
        "added_nodes": added,
        "removed_nodes": removed,
        "changed_nodes": changed,
        "has_changes": bool(added or removed or changed),
    }
