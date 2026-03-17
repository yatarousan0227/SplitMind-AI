"""Runtime entry point for SplitMind-AI.

Provides both a programmatic API and a CLI entry point for running
single-turn and multi-turn conversations.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import os
import sys
from pathlib import Path
from typing import Any

from splitmind_ai.app.language import detect_response_language
from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.app.llm import create_chat_llm
from splitmind_ai.app.logging_utils import configure_logging, preview_text
from splitmind_ai.app.settings import PROJECT_ROOT, get_default_persona, load_settings

logger = logging.getLogger(__name__)


def _build_turn_state(
    *,
    user_message: str,
    session_id: str,
    user_id: str,
    response_language: str | None,
    turn_count: int,
    latest_state: dict[str, Any],
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the next graph input state, carrying forward prior turn slices."""
    resolved_response_language = detect_response_language(user_message, response_language)
    state: dict[str, Any] = {
        "request": {
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "message": user_message,
            "action": "chat",
            "response_language": resolved_response_language,
        },
        "response": {},
        "_internal": {
            "is_first_turn": turn_count == 0,
            "turn_count": turn_count,
        },
    }

    if turn_count == 0:
        return state

    for slice_name in ("persona", "relationship", "mood", "memory", "drive_state", "inhibition_state"):
        slice_value = latest_state.get(slice_name)
        if isinstance(slice_value, dict):
            state[slice_name] = copy.deepcopy(slice_value)

    prior_internal = latest_state.get("_internal", {})
    if isinstance(prior_internal, dict):
        session = prior_internal.get("session")
        if isinstance(session, dict):
            state["_internal"]["session"] = copy.deepcopy(session)

    prior_conversation = latest_state.get("conversation", {})
    recent_messages = [
        {"role": msg.get("role", ""), "content": msg.get("content", "")}
        for msg in messages[-6:]
    ]
    state["conversation"] = {
        "recent_messages": recent_messages,
        "summary": (
            prior_conversation.get("summary")
            if isinstance(prior_conversation, dict)
            else None
        ),
        "turn_count": turn_count + 1,
    }

    return state


async def run_turn(
    user_message: str,
    session_id: str = "cli-session",
    persona_name: str | None = None,
    vault_path: str | None = None,
    user_id: str = "default",
    response_language: str | None = None,
) -> dict[str, Any]:
    """Execute a single conversation turn.

    Args:
        user_message: The user's input text.
        session_id: Session identifier.
        persona_name: Override persona name. Uses config default if None.
        vault_path: Path to Obsidian vault. None uses config default.
        user_id: User identifier for vault storage.

    Returns:
        The final agent state dict after the turn.
    """
    from splitmind_ai.app.graph import build_splitmind_graph

    configure_logging()
    settings = load_settings()

    if persona_name is None:
        persona_name = get_default_persona(settings)

    if vault_path is None and settings.vault.enabled:
        vault_path = str(Path(settings.vault.path).resolve())
        if not Path(vault_path).is_absolute():
            vault_path = str(PROJECT_ROOT / settings.vault.path)

    llm = create_chat_llm(settings)

    compiled_graph = build_splitmind_graph(
        llm=llm,
        persona_name=persona_name,
        vault_path=vault_path,
    )

    initial_state: dict[str, Any] = {
        "request": {
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "message": user_message,
            "action": "chat",
            "response_language": detect_response_language(user_message, response_language),
        },
        "response": {},
        "_internal": {
            "is_first_turn": True,
            "turn_count": 0,
        },
    }

    logger.debug(
        "run_turn start session_id=%s user_id=%s persona=%s vault_path=%s message=%s",
        session_id,
        user_id,
        persona_name,
        vault_path,
        preview_text(user_message),
    )
    result = await compiled_graph.ainvoke(initial_state)
    logger.debug(
        "run_turn complete session_id=%s status=%s decision=%s response=%s",
        session_id,
        result.get("_internal", {}).get("status"),
        result.get("_internal", {}).get("decision"),
        preview_text(result.get("response", {}).get("final_response_text")),
    )
    return result


async def run_session(
    persona_name: str | None = None,
    vault_path: str | None = None,
    user_id: str = "default",
    session_id: str | None = None,
    response_language: str | None = None,
) -> None:
    """Run an interactive multi-turn session in the terminal."""
    import uuid

    from splitmind_ai.app.graph import build_splitmind_graph

    configure_logging()
    settings = load_settings()

    if persona_name is None:
        persona_name = get_default_persona(settings)
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]
    if vault_path is None and settings.vault.enabled:
        vault_path = str((PROJECT_ROOT / settings.vault.path).resolve())

    llm = create_chat_llm(settings)

    compiled_graph = build_splitmind_graph(
        llm=llm,
        persona_name=persona_name,
        vault_path=vault_path,
    )

    vault_store: VaultStore | None = None
    if vault_path:
        vault_store = VaultStore(vault_path)

    print(f"\n[Session: {session_id} | Persona: {persona_name}]")
    print("Type 'quit' to exit, 'trace' to toggle trace display.\n")

    show_trace = False
    turn_count = 0
    latest_state: dict[str, Any] = {}
    messages: list[dict[str, Any]] = []
    session_event_log: list[dict[str, Any]] = []
    initial_relationship: dict[str, Any] = {}

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "trace":
            show_trace = not show_trace
            print(f"[Trace display: {'ON' if show_trace else 'OFF'}]")
            continue

        messages.append({"role": "user", "content": user_input})
        state = _build_turn_state(
            user_message=user_input,
            session_id=session_id,
            user_id=user_id,
            response_language=response_language,
            turn_count=turn_count,
            latest_state=latest_state,
            messages=messages,
        )

        logger.debug(
            "run_session turn start session_id=%s turn_count=%s message=%s",
            session_id,
            turn_count,
            preview_text(user_input),
        )
        result = await compiled_graph.ainvoke(state)
        turn_count += 1
        logger.debug(
            "run_session turn complete session_id=%s turn_count=%s status=%s response=%s",
            session_id,
            turn_count,
            result.get("_internal", {}).get("status"),
            preview_text(result.get("response", {}).get("final_response_text")),
        )

        # Record initial relationship for delta calculation
        if turn_count == 1:
            initial_relationship = dict(result.get("relationship", {}))

        # Accumulate event flags across the session
        turn_events = result.get("_internal", {}).get("event_flags", {})
        fired = [k for k, v in turn_events.items() if v]
        if fired:
            session_event_log.append({"turn": turn_count, "events": fired})

        response = result.get("response", {})
        final_text = response.get("final_response_text", "(no response)")
        messages.append({"role": "assistant", "content": final_text})
        latest_state = result
        print(f"\nAgent: {final_text}\n")

        if show_trace:
            _print_trace(result)

    # Save session summary on exit
    if turn_count > 0 and vault_store is not None:
        try:
            summary = _build_session_summary(
                messages=messages,
                turn_count=turn_count,
                initial_relationship=initial_relationship,
                final_state=latest_state,
                event_log=session_event_log,
            )
            vault_store.save_session_summary(
                user_id=user_id,
                session_id=session_id,
                summary=summary["text"],
                turn_count=turn_count,
                dominant_mood=latest_state.get("mood", {}).get("base_mood", "calm"),
                key_events=summary["key_events"],
            )
            logger.info("Session summary saved for session_id=%s", session_id)
        except Exception:
            logger.warning("Failed to save session summary", exc_info=True)


def _build_session_summary(
    messages: list[dict[str, Any]],
    turn_count: int,
    initial_relationship: dict[str, Any],
    final_state: dict[str, Any],
    event_log: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a rule-based session summary dict.

    Returns:
        {
            "text": str,
            "key_events": list[str],
        }
    """
    final_rel = final_state.get("relationship", {})
    final_mood = final_state.get("mood", {}).get("base_mood", "calm")

    # Relationship delta
    rel_changes: list[str] = []
    for key in ("trust", "intimacy", "tension", "distance"):
        before = initial_relationship.get(key)
        after = final_rel.get(key)
        if before is not None and after is not None:
            delta = after - before
            if abs(delta) >= 0.01:
                sign = "+" if delta > 0 else ""
                rel_changes.append(f"{key}: {before:.2f} → {after:.2f} ({sign}{delta:.2f})")

    # All fired events across session
    all_events: list[str] = []
    for entry in event_log:
        all_events.extend(entry.get("events", []))
    unique_events = list(dict.fromkeys(all_events))  # preserve order, deduplicate

    # First and last user messages
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    first_msg = user_msgs[0][:100] if user_msgs else ""
    last_msg = user_msgs[-1][:100] if len(user_msgs) > 1 else ""

    # Build summary text
    parts: list[str] = [f"{turn_count}ターンの会話。"]
    if unique_events:
        parts.append(f"発火イベント: {', '.join(unique_events)}。")
    if rel_changes:
        parts.append(f"関係値変化: {'; '.join(rel_changes)}。")
    parts.append(f"最終ムード: {final_mood}。")
    if first_msg:
        parts.append(f"冒頭の発話: 「{first_msg}」")
    if last_msg:
        parts.append(f"最後の発話: 「{last_msg}」")

    return {
        "text": " ".join(parts),
        "key_events": unique_events,
    }


def _print_trace(result: dict[str, Any]) -> None:
    """Print trace information from a turn result."""
    trace = result.get("trace", {})
    dynamics = trace.get("internal_dynamics", {})
    motivational = trace.get("motivational_state", {})
    if motivational or dynamics:
        drive_state = motivational.get("drive_state", {}) or result.get("drive_state", {}) or {}
        top_drives = list(drive_state.get("top_drives", []) or [])
        primary = top_drives[0] if top_drives else {}
        target = primary.get("target") or ((drive_state.get("drive_targets", {}) or {}).get(primary.get("name"), "?"))
        defense = dynamics.get("defense_output", {}).get("selected_mechanism", "?")
        print(f"  [Trace] Top drive: {primary.get('name', '?')}")
        print(f"  [Trace] Target: {target}")
        print(f"  [Trace] Defense mechanism: {defense}")

    supervisor = trace.get("supervisor", {})
    if supervisor:
        print(f"  [Trace] Leakage: {supervisor.get('leakage_level', '?')}")
        print(f"  [Trace] Surface: {supervisor.get('surface_intent', '?')}")

    surface = trace.get("surface_realization", {})
    if surface:
        signature = surface.get("latent_drive_signature", {}) or {}
        print(f"  [Trace] Latent signal: {signature.get('latent_signal_hint', '?')}")
        blocked = surface.get("blocked_by_inhibition", []) or []
        if blocked:
            print(f"  [Trace] Blocked by inhibition: {', '.join(blocked)}")

    relationship = result.get("relationship", {})
    if relationship:
        print(f"  [State] Trust: {relationship.get('trust', 0):.2f}")
        print(f"  [State] Tension: {relationship.get('tension', 0):.2f}")
        print(f"  [State] Intimacy: {relationship.get('intimacy', 0):.2f}")

    mood = result.get("mood", {})
    if mood:
        print(f"  [State] Mood: {mood.get('base_mood', '?')}")

    commit = trace.get("memory_commit", {})
    if commit:
        print(f"  [Vault] Committed: {commit.get('vault_committed', False)}")

    print()


def main() -> None:
    """CLI entry point: ``python -m splitmind_ai.app.runtime``."""
    configure_logging()

    if "--session" in sys.argv:
        asyncio.run(run_session())
        return

    user_message = " ".join(
        a for a in sys.argv[1:] if not a.startswith("--")
    ) or "今日は他の人とすごく楽しかった"

    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}\n")

    result = asyncio.run(run_turn(user_message))

    response = result.get("response", {})
    final_text = response.get("final_response_text", "(no response)")
    print(f"\n{'='*60}")
    print(f"Agent: {final_text}")
    print(f"{'='*60}\n")

    _print_trace(result)


if __name__ == "__main__":
    main()
