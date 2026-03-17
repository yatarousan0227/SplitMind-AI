"""Streamlit research UI for SplitMind-AI.

Run with:
    streamlit run src/splitmind_ai/ui/app.py -- --user-id alice
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import logging
import os
import sys
import uuid
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import streamlit as st

from splitmind_ai.app.language import detect_response_language
from splitmind_ai.app.logging_utils import configure_logging, preview_text
from splitmind_ai.app.llm import create_chat_llm
from splitmind_ai.app.settings import PROJECT_ROOT, get_default_persona, load_settings
from splitmind_ai.personas.loader import list_personas
from splitmind_ai.ui.dashboard import build_current_dashboard, build_history_rows, build_turn_snapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

def _resolve_startup_user_id(
    argv: list[str] | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--user-id")
    args, _ = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    raw_user_id = args.user_id
    if raw_user_id is None:
        raw_user_id = (environ if environ is not None else os.environ).get("SPLITMIND_USER_ID")

    candidate = (raw_user_id or "").strip()
    if not candidate:
        return "default"

    candidate = candidate.replace("/", "_").replace("\\", "_")
    if candidate in {".", ".."}:
        return "default"
    return candidate


def _init_session_state(
    session_state: MutableMapping[str, Any] | None = None,
    startup_user_id: str | None = None,
) -> None:
    target = session_state if session_state is not None else st.session_state
    if "messages" not in target:
        target["messages"] = []
    if "session_id" not in target:
        target["session_id"] = str(uuid.uuid4())[:8]
    if "turn_count" not in target:
        target["turn_count"] = 0
    if "traces" not in target:
        target["traces"] = []
    if "latest_state" not in target:
        target["latest_state"] = {}
    if "turn_snapshots" not in target:
        target["turn_snapshots"] = []
    if "user_id" not in target:
        target["user_id"] = startup_user_id or "default"
    if "response_language" not in target:
        target["response_language"] = "auto"


def _reset_session_state(session_state: MutableMapping[str, Any] | None = None) -> None:
    target = session_state if session_state is not None else st.session_state
    target["messages"] = []
    target["session_id"] = str(uuid.uuid4())[:8]
    target["turn_count"] = 0
    target["traces"] = []
    target["latest_state"] = {}
    target["turn_snapshots"] = []


# ---------------------------------------------------------------------------
# Core execution
# ---------------------------------------------------------------------------

def _runtime_cache_key(settings: Any, persona_name: str, vault_path: str | None) -> tuple[Any, ...]:
    """Build a stable key for reusing the compiled graph and LLM in Streamlit."""
    return (
        settings.llm.provider,
        settings.llm.model,
        settings.llm.azure_deployment,
        settings.llm.api_version,
        persona_name,
        str(Path(vault_path).resolve()) if vault_path else None,
    )


def _get_or_create_runtime(
    *,
    session_state: MutableMapping[str, Any] | None,
    settings: Any,
    persona_name: str,
    vault_path: str | None,
) -> Any:
    """Reuse the compiled graph within the Streamlit session when config is unchanged."""
    from splitmind_ai.app.graph import build_splitmind_graph

    target = session_state if session_state is not None else st.session_state
    cache_key = _runtime_cache_key(settings, persona_name, vault_path)
    cached = target.get("_runtime_cache")

    if isinstance(cached, dict) and cached.get("cache_key") == cache_key:
        return cached["compiled"]

    llm = create_chat_llm(settings)
    compiled = build_splitmind_graph(
        llm=llm,
        persona_name=persona_name,
        vault_path=vault_path,
    )
    target["_runtime_cache"] = {
        "cache_key": cache_key,
        "compiled": compiled,
    }
    return compiled

def _run_turn(
    user_message: str,
    persona_name: str,
    vault_path: str | None,
    user_id: str,
    response_language: str | None,
) -> dict[str, Any]:
    """Execute a single turn via the graph."""
    configure_logging()
    settings = load_settings()
    compiled = _get_or_create_runtime(
        session_state=st.session_state,
        settings=settings,
        persona_name=persona_name,
        vault_path=vault_path,
    )

    state = _build_turn_state(
        user_message=user_message,
        session_id=st.session_state.session_id,
        user_id=user_id,
        response_language=response_language,
        turn_count=st.session_state.turn_count,
        latest_state=st.session_state.latest_state,
        messages=st.session_state.messages,
    )

    logger.debug(
        "ui turn start session_id=%s turn_count=%s persona=%s message=%s",
        st.session_state.session_id,
        st.session_state.turn_count,
        persona_name,
        preview_text(user_message),
    )
    result = asyncio.run(compiled.ainvoke(state))
    st.session_state.turn_count += 1
    logger.debug(
        "ui turn complete session_id=%s turn_count=%s status=%s response=%s",
        st.session_state.session_id,
        st.session_state.turn_count,
        result.get("_internal", {}).get("status"),
        preview_text(result.get("response", {}).get("final_response_text")),
    )
    return result


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


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar() -> tuple[str, bool, str | None, str]:
    """Render sidebar controls and return persona, trace mode, vault path, and language mode."""
    st.sidebar.title("SplitMind-AI Research")

    # Persona selector
    available = list_personas()
    settings = load_settings()
    default_persona = get_default_persona(settings)
    default_idx = available.index(default_persona) if default_persona in available else 0
    persona_name = st.sidebar.selectbox("Persona", available, index=default_idx)

    # Trace mode
    trace_mode = st.sidebar.toggle("Show trace", value=True)

    # Vault
    vault_enabled = st.sidebar.toggle("Vault persistence", value=settings.vault.enabled)
    vault_path = str((PROJECT_ROOT / settings.vault.path).resolve()) if vault_enabled else None

    language_options = {
        "Auto": "auto",
        "Japanese": "ja",
        "English": "en",
    }
    language_labels = list(language_options.keys())
    current_language = st.session_state.get("response_language", "auto")
    default_language = next(
        (label for label, value in language_options.items() if value == current_language),
        "Auto",
    )
    selected_label = st.sidebar.selectbox(
        "Response language / 応答言語",
        language_labels,
        index=language_labels.index(default_language),
    )
    st.session_state["response_language"] = language_options[selected_label]

    # Reset session
    if st.sidebar.button("Reset Session"):
        _reset_session_state()
        st.rerun()

    # Session info
    st.sidebar.divider()
    st.sidebar.caption(f"User: {st.session_state.user_id}")
    st.sidebar.caption(f"Session: {st.session_state.session_id}")
    st.sidebar.caption(f"Turns: {st.session_state.turn_count}")

    return persona_name, trace_mode, vault_path, st.session_state["response_language"]


# ---------------------------------------------------------------------------
# State display
# ---------------------------------------------------------------------------

def _render_state_panel(state: dict[str, Any]) -> None:
    """Render minimal session summary in the sidebar."""
    relationship = state.get("relationship", {})
    drive_state = state.get("drive_state", {})
    conversation_policy = state.get("conversation_policy", {})
    if not relationship and not drive_state:
        return

    st.sidebar.divider()
    st.sidebar.subheader("Current Summary")

    tensions = relationship.get("unresolved_tensions", [])
    if tensions:
        top = max(tensions, key=lambda t: t.get("intensity", 0))
        st.sidebar.caption(
            f"Top tension: {top.get('theme', '?')} ({top.get('intensity', 0):.2f})"
        )
    else:
        st.sidebar.caption("Top tension: none")

    top_drives = list(drive_state.get("top_drives", []) or [])
    if top_drives:
        primary = top_drives[0] or {}
        target = primary.get("target") or (drive_state.get("drive_targets", {}) or {}).get(primary.get("name"), "")
        target_suffix = f" -> {target}" if target else ""
        st.sidebar.caption(
            f"Top drive: {primary.get('name', '?')} ({float(primary.get('value', 0.0)):.2f}){target_suffix}"
        )
    else:
        st.sidebar.caption("Top drive: none")

    selected_mode = conversation_policy.get("selected_mode")
    if selected_mode:
        st.sidebar.caption(f"Mode: {selected_mode}")


def _inject_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
        .sm-flow {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-bottom: 0.85rem;
        }
        .sm-flow-card {
            flex: 1 1 150px;
            min-height: 108px;
            padding: 0.85rem 0.95rem;
            border-radius: 18px;
            border: 1px solid rgba(18, 53, 91, 0.08);
            background: linear-gradient(180deg, #fffaf4 0%, #f6efe6 100%);
            box-shadow: 0 8px 22px rgba(18, 53, 91, 0.08);
        }
        .sm-flow-stage {
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7f6a53;
            margin-bottom: 0.35rem;
        }
        .sm-flow-value {
            font-size: 1rem;
            line-height: 1.2;
            font-weight: 700;
            color: #12355b;
            margin-bottom: 0.4rem;
        }
        .sm-flow-note {
            font-size: 0.84rem;
            line-height: 1.35;
            color: #5a6473;
        }
        .sm-story {
            margin: 0 0 1rem 0;
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #12355b 0%, #355c7d 100%);
            color: #fffaf4;
            box-shadow: 0 10px 28px rgba(18, 53, 91, 0.18);
        }
        .sm-story-label {
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            opacity: 0.78;
            margin-bottom: 0.35rem;
        }
        .sm-story-body {
            font-size: 1rem;
            line-height: 1.45;
        }
        .sm-meter {
            margin-bottom: 0.85rem;
        }
        .sm-meter-header {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            font-size: 0.9rem;
            margin-bottom: 0.28rem;
            color: #12355b;
        }
        .sm-meter-track {
            width: 100%;
            height: 12px;
            background: #eadfce;
            border-radius: 999px;
            overflow: hidden;
        }
        .sm-meter-fill {
            height: 100%;
            border-radius: 999px;
        }
        .sm-meter-note {
            margin-top: 0.2rem;
            font-size: 0.78rem;
            color: #7f6a53;
        }
        .sm-stack {
            display: grid;
            gap: 0.7rem;
        }
        .sm-chip-panel {
            padding: 0.95rem 1rem;
            border-radius: 18px;
            background: linear-gradient(180deg, #fffaf4 0%, #f8f0e8 100%);
            border: 1px solid rgba(18, 53, 91, 0.08);
        }
        .sm-mini-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.6rem;
        }
        .sm-mini-card {
            padding: 0.75rem 0.85rem;
            border-radius: 14px;
            background: #fffdf9;
            border: 1px solid rgba(18, 53, 91, 0.08);
        }
        .sm-mini-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7f6a53;
            margin-bottom: 0.28rem;
        }
        .sm-mini-value {
            font-size: 0.92rem;
            line-height: 1.3;
            color: #12355b;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_story_flow(story_steps: list[dict[str, str]], drive_story: str) -> None:
    st.markdown(
        (
            '<div class="sm-story">'
            '<div class="sm-story-label">Current Turn Read</div>'
            f'<div class="sm-story-body">{drive_story}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if not story_steps:
        st.caption("No drive flow available yet.")
        return

    cards = []
    for step in story_steps:
        cards.append(
            '<div class="sm-flow-card">'
            f'<div class="sm-flow-stage">{step.get("stage", "")}</div>'
            f'<div class="sm-flow-value">{step.get("value", "")}</div>'
            f'<div class="sm-flow-note">{step.get("note", "")}</div>'
            "</div>"
        )
    st.markdown(f'<div class="sm-flow">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_pressure_panel(residue_rows: list[dict[str, Any]]) -> None:
    if not residue_rows:
        st.caption("No residue profile available.")
        return

    notes = {
        "intensity": "How much drive is active right now.",
        "frustration": "How much remains unsatisfied.",
        "carryover": "How much this turn inherits from the last one.",
        "suppression_load": "How much pressure is being held back.",
        "satiation": "How much the exchange already soothed the drive.",
    }
    parts = []
    for row in residue_rows:
        color = _meter_color(str(row.get("tone", "")))
        value = float(row.get("value", 0.0))
        parts.append(
            '<div class="sm-meter">'
            '<div class="sm-meter-header">'
            f'<span>{row.get("label", "")}</span><strong>{value:.2f}</strong>'
            "</div>"
            '<div class="sm-meter-track">'
            f'<div class="sm-meter-fill" style="width:{value * 100:.0f}%;background:{color};"></div>'
            "</div>"
            f'<div class="sm-meter-note">{notes.get(row.get("key", ""), "")}</div>'
            "</div>"
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def _render_drive_stack(drive_rows: list[dict[str, Any]]) -> None:
    if not drive_rows:
        st.caption("No active drives.")
        return

    stack = []
    for row in drive_rows:
        target = f" -> {row['target']}" if row.get("target") else ""
        width = max(8.0, float(row.get("value", 0.0)) * 100)
        stack.append(
            '<div class="sm-meter">'
            '<div class="sm-meter-header">'
            f'<span>{row.get("label", "unknown")}{target}</span>'
            f'<strong>{float(row.get("value", 0.0)):.2f}</strong>'
            "</div>"
            '<div class="sm-meter-track">'
            f'<div class="sm-meter-fill" style="width:{width:.0f}%;background:#d17a22;"></div>'
            "</div>"
            "</div>"
        )
    st.markdown(f'<div class="sm-stack">{"".join(stack)}</div>', unsafe_allow_html=True)


def _render_surface_panel(current: dict[str, Any], active_themes: list[str]) -> None:
    drive = current.get("drive", {}) or {}
    policy = current.get("policy", {}) or {}
    supervisor = current.get("supervisor", {}) or {}
    signature = drive.get("latent_drive_signature", {}) or {}
    blocked = ", ".join(policy.get("blocked_by_inhibition", []) or []) or "none"

    cards = [
        ("Latent signal", signature.get("latent_signal_hint") or "contained"),
        ("Satisfaction goal", policy.get("satisfaction_goal") or "hold state"),
        ("Blocked by inhibition", blocked),
        ("Leakage", f"{float(supervisor.get('leakage_level', 0.0)):.2f}"),
    ]
    html_cards = []
    for label, value in cards:
        html_cards.append(
            '<div class="sm-mini-card">'
            f'<div class="sm-mini-label">{label}</div>'
            f'<div class="sm-mini-value">{value}</div>'
            "</div>"
        )

    st.markdown(
        (
            '<div class="sm-chip-panel">'
            '<div class="sm-mini-grid">'
            f'{"".join(html_cards)}'
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if active_themes:
        st.markdown("Active themes")
        st.markdown(_format_badges(active_themes), unsafe_allow_html=True)


def _meter_color(tone: str) -> str:
    return {
        "heat": "linear-gradient(90deg, #d17a22 0%, #b23a48 100%)",
        "risk": "linear-gradient(90deg, #b23a48 0%, #8f1d2c 100%)",
        "carry": "linear-gradient(90deg, #3c6e71 0%, #12355b 100%)",
        "block": "linear-gradient(90deg, #6a4c93 0%, #355c7d 100%)",
        "release": "linear-gradient(90deg, #6b8f71 0%, #3c6e71 100%)",
    }.get(tone, "#d17a22")


def _render_dashboard(turn_snapshots: list[dict[str, Any]]) -> None:
    st.subheader("Session Dashboard")
    if not turn_snapshots:
        st.info("Start chatting to populate the session dashboard.")
        return

    _inject_dashboard_styles()
    dashboard = build_current_dashboard(turn_snapshots)
    history = build_history_rows(turn_snapshots)
    current = dashboard["current"] or {}

    _render_kpi_cards(current, dashboard["turns"])

    col1, col2 = st.columns((7, 5))
    with col1:
        st.caption("Drive Flow")
        _render_story_flow(dashboard["story_steps"], dashboard["drive_story"])
    with col2:
        st.caption("Pressure Profile")
        _render_pressure_panel(dashboard["residue_rows"])

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Relationship Over Time")
        st.plotly_chart(
            _make_multi_line_chart(
                history["relationship"],
                title="Relationship signals",
                yaxis_title="score",
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col2:
        st.caption("Affect Over Time")
        st.plotly_chart(
            _make_multi_line_chart(
                history["affect"],
                title="Affective signals",
                yaxis_title="score",
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    if history["timing"]:
        st.caption("Node Timing Over Time")
        st.plotly_chart(
            _make_timing_chart(history["timing"]),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Appraisal Map")
        st.plotly_chart(
            _make_radar_chart(dashboard["appraisal_radar"], title="Appraisal"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col2:
        st.caption("Self-State Map")
        st.plotly_chart(
            _make_radar_chart(dashboard["self_state_radar"], title="Self-state"),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    col1, col2 = st.columns((3, 2))
    with col1:
        st.caption("Action Candidates")
        st.plotly_chart(
            _make_candidate_chart(dashboard["candidate_rows"]),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col2:
        st.caption("Event Timeline")
        _render_event_groups(dashboard["event_groups"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Top Drives")
        _render_drive_stack(dashboard["drive_rows"])
    with col2:
        st.caption("Surface Trace")
        _render_surface_panel(current, dashboard["active_themes"])
    with col3:
        st.caption("Top Unresolved Tensions")
        tensions = dashboard["unresolved_tensions"]
        if tensions:
            for tension in tensions:
                source = f" ({tension['source']})" if tension.get("source") else ""
                st.markdown(
                    f"- **{tension['theme']}**: {tension['intensity']:.2f}{source}"
                )
        else:
            st.caption("No unresolved tensions.")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Memory Counts")
        counts = dashboard["memory_counts"]
        st.markdown(f"- Emotional memories: **{counts.get('emotional_memories', 0)}**")
        st.markdown(f"- Semantic preferences: **{counts.get('semantic_preferences', 0)}**")
        st.markdown(f"- Active themes: **{counts.get('active_themes', 0)}**")
    with col2:
        timing_rows = dashboard["timing_rows"]
        if timing_rows:
            st.caption("Latest Node Timing")
            for row in timing_rows:
                st.markdown(f"- {row['label']}: **{row['value']:.2f} ms**")


def _render_kpi_cards(current: dict[str, Any], turns: int) -> None:
    mood = (current.get("mood", {}) or {}).get("base_mood") or "unknown"
    drive = current.get("drive", {}) or {}
    primary_drive = drive.get("primary_drive") or "unknown"
    top_target = drive.get("top_target") or "none"
    selected_mode = (current.get("policy", {}) or {}).get("selected_mode") or "unknown"
    leakage = (current.get("supervisor", {}) or {}).get("leakage_level", 0.0)

    cards = st.columns(6)
    cards[0].metric("Current Mood", str(mood))
    cards[1].metric("Top Drive", str(primary_drive))
    cards[2].metric("Top Target", str(top_target))
    cards[3].metric("Selected Mode", str(selected_mode))
    cards[4].metric("Leakage", f"{float(leakage):.2f}")
    cards[5].metric("Turns", str(turns))


def _make_multi_line_chart(
    rows: list[dict[str, Any]],
    *,
    title: str,
    yaxis_title: str,
):
    import plotly.graph_objects as go

    figure = go.Figure()
    metric_names = list(dict.fromkeys(row["metric"] for row in rows))
    palette = [
        "#12355B",
        "#3C6E71",
        "#D17A22",
        "#B23A48",
        "#6A4C93",
    ]
    for index, metric in enumerate(metric_names):
        metric_rows = [row for row in rows if row["metric"] == metric]
        figure.add_trace(go.Scatter(
            x=[row["turn"] for row in metric_rows],
            y=[row["value"] for row in metric_rows],
            mode="lines+markers",
            name=metric.replace("_", " "),
            line={"width": 3, "color": palette[index % len(palette)]},
        ))

    figure.update_layout(
        title=title,
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F3EE",
        yaxis={"range": [0, 1], "title": yaxis_title},
        xaxis={"title": "turn", "dtick": 1},
        legend={"orientation": "h", "y": -0.2},
    )
    return figure


def _make_radar_chart(rows: list[dict[str, Any]], *, title: str):
    import plotly.graph_objects as go

    axes = [row["axis"].replace("_", " ") for row in rows]
    values = [row["value"] for row in rows]
    if axes and values:
        axes = axes + [axes[0]]
        values = values + [values[0]]

    figure = go.Figure()
    figure.add_trace(go.Scatterpolar(
        r=values or [0.0],
        theta=axes or ["empty"],
        fill="toself",
        line={"color": "#B23A48", "width": 2},
        fillcolor="rgba(178,58,72,0.18)",
        name=title,
    ))
    figure.update_layout(
        title=title,
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        polar={"radialaxis": {"range": [0, 1], "showticklabels": True, "ticks": ""}},
        showlegend=False,
    )
    return figure


def _make_candidate_chart(rows: list[dict[str, Any]]):
    import plotly.graph_objects as go

    figure = go.Figure()
    if rows:
        ordered = sorted(rows, key=lambda row: row["score"], reverse=True)
        figure.add_trace(go.Bar(
            x=[row["score"] for row in ordered],
            y=[row["label"] for row in ordered],
            orientation="h",
            marker={"color": "#D17A22"},
            text=[f"{row['score']:.2f}" for row in ordered],
            textposition="outside",
        ))
    figure.update_layout(
        title="Policy options",
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F3EE",
        xaxis={"range": [0, 1], "title": "score"},
        yaxis={"title": ""},
        showlegend=False,
    )
    return figure


def _make_timing_chart(rows: list[dict[str, Any]]):
    import plotly.graph_objects as go

    figure = go.Figure()
    metric_names = list(dict.fromkeys(row["metric"] for row in rows))
    palette = [
        "#12355B",
        "#3C6E71",
        "#D17A22",
        "#B23A48",
        "#6A4C93",
        "#687864",
        "#C06C84",
        "#355C7D",
    ]
    for index, metric in enumerate(metric_names):
        metric_rows = [row for row in rows if row["metric"] == metric]
        figure.add_trace(go.Scatter(
            x=[row["turn"] for row in metric_rows],
            y=[row["value"] for row in metric_rows],
            mode="lines+markers",
            name=metric.replace("_", " "),
            line={"width": 3, "color": palette[index % len(palette)]},
        ))

    figure.update_layout(
        title="Node timing",
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F3EE",
        yaxis={"title": "ms"},
        xaxis={"title": "turn", "dtick": 1},
        legend={"orientation": "h", "y": -0.2},
    )
    return figure


def _render_event_groups(event_groups: list[dict[str, Any]]) -> None:
    if not event_groups:
        st.caption("No events fired yet.")
        return

    for group in event_groups:
        st.markdown(f"**Turn {group['turn']}**")
        st.markdown(_format_badges(group["events"]), unsafe_allow_html=True)


def _format_badges(items: list[str]) -> str:
    if not items:
        return ""
    badges = []
    for item in items:
        badges.append(
            "<span style=\"display:inline-block;padding:0.2rem 0.55rem;margin:0 0.35rem 0.35rem 0;"
            "border-radius:999px;background:#EFE4D6;color:#12355B;font-size:0.85rem;\">"
            f"{item}</span>"
        )
    return "".join(badges)


# ---------------------------------------------------------------------------
# Trace display
# ---------------------------------------------------------------------------

def _render_trace(trace_data: dict[str, Any]) -> None:
    """Render trace information for a single turn."""
    dynamics = trace_data.get("internal_dynamics", {})
    motivational = trace_data.get("motivational_state", {})
    supervisor = trace_data.get("supervisor", {})
    surface = trace_data.get("surface_realization", {})
    commit = trace_data.get("memory_commit", {})

    col1, col2 = st.columns(2)

    with col1:
        if motivational or dynamics:
            st.caption("Motivational State")
            drive_state = (motivational.get("drive_state", {}) or {})
            top_drives = list(drive_state.get("top_drives", []) or [])
            primary = top_drives[0] if top_drives else {}
            defense = dynamics.get("defense_output", {}).get("selected_mechanism", "?")
            target = primary.get("target") or ((drive_state.get("drive_targets", {}) or {}).get(primary.get("name"), "?"))
            st.markdown(f"- **Top drive**: {primary.get('name', '?')}")
            st.markdown(f"- **Target**: {target}")
            st.markdown(f"- **Defense**: {defense}")
            signature = surface.get("latent_drive_signature", {}) or {}
            st.markdown(f"- **Intensity**: {float(signature.get('intensity', 0.0)):.2f}")

    with col2:
        if supervisor or surface:
            st.caption("Surface Trace")
            st.markdown(f"- **Surface**: {supervisor.get('surface_intent', '?')}")
            st.markdown(f"- **Hidden**: {supervisor.get('hidden_pressure', '?')}")
            st.markdown(f"- **Mask goal**: {supervisor.get('mask_goal', '?')}")
            st.markdown(f"- **Leakage**: {supervisor.get('leakage_level', '?')}")
            st.markdown(f"- **Containment**: {supervisor.get('containment_success', '?')}")
            st.markdown(f"- **Latent signal**: {((surface.get('latent_drive_signature', {}) or {}).get('latent_signal_hint') or '?')}")
            blocked = surface.get("blocked_by_inhibition", []) or []
            if blocked:
                st.markdown(f"- **Blocked by inhibition**: {', '.join(blocked)}")
            goal = surface.get("satisfaction_goal")
            if goal:
                st.markdown(f"- **Satisfaction goal**: {goal}")

    if commit:
        flags = commit.get("event_flags", {})
        active = [k for k, v in flags.items() if v]
        if active:
            st.caption(f"Event flags: {', '.join(active)}")

    timing_rows = _collect_trace_timings(trace_data)
    if timing_rows:
        st.caption("Timing")
        for label, value in timing_rows:
            st.markdown(f"- **{label}**: {value:.2f} ms")

    # Downloadable raw JSON
    with st.expander("Raw trace JSON"):
        st.json(trace_data)


def _collect_trace_timings(trace_data: dict[str, Any]) -> list[tuple[str, float]]:
    timing_rows: list[tuple[str, float]] = []
    for section_name, section in trace_data.items():
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if not key.endswith("_ms"):
                continue
            try:
                timing_rows.append((section_name, float(value)))
            except (TypeError, ValueError):
                continue
            break
    return timing_rows


def _assistant_trace_indices(messages: list[dict[str, Any]]) -> list[int | None]:
    """Map each chat message to its assistant-trace index, if any."""
    indices: list[int | None] = []
    assistant_count = 0

    for msg in messages:
        if msg.get("role") == "assistant":
            indices.append(assistant_count)
            assistant_count += 1
        else:
            indices.append(None)

    return indices


def _render_chat_history(*, show_trace: bool) -> None:
    trace_indices = _assistant_trace_indices(st.session_state.messages)
    for msg, trace_idx in zip(st.session_state.messages, trace_indices):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
        if show_trace and trace_idx is not None and trace_idx < len(st.session_state.traces):
            with st.expander(f"Trace (turn {trace_idx + 1})", expanded=False):
                _render_trace(st.session_state.traces[trace_idx])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    configure_logging()
    st.set_page_config(
        page_title="SplitMind-AI Research",
        page_icon="🧠",
        layout="wide",
    )

    _init_session_state(startup_user_id=_resolve_startup_user_id())
    persona_name, trace_mode, vault_path, response_language = _render_sidebar()
    _render_state_panel(st.session_state.latest_state)

    st.title("SplitMind-AI")

    tabs = st.tabs(["Chat", "Dashboard"])
    chat_tab = tabs[0]
    dashboard_tab = tabs[1]

    with chat_tab:
        _render_chat_history(show_trace=trace_mode)

        if user_input := st.chat_input("Send a message..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)

            with st.spinner("Thinking..."):
                try:
                    result = _run_turn(
                        user_input,
                        persona_name,
                        vault_path,
                        st.session_state.user_id,
                        response_language,
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
                    return

            response = result.get("response", {})
            final_text = response.get("final_response_text", "(no response)")

            st.session_state.messages.append({"role": "assistant", "content": final_text})
            st.session_state.latest_state = result
            st.session_state.traces.append(result.get("trace", {}))
            st.session_state.turn_snapshots.append(
                build_turn_snapshot(result, st.session_state.turn_count)
            )

            with st.chat_message("assistant"):
                st.write(final_text)

            if trace_mode:
                with st.expander(
                    f"Trace (turn {st.session_state.turn_count})",
                    expanded=True,
                ):
                    _render_trace(result.get("trace", {}))

            st.rerun()

    with dashboard_tab:
        _render_dashboard(st.session_state.turn_snapshots)


if __name__ == "__main__":
    main()
