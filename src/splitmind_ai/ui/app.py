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
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from splitmind_ai.app.language import detect_response_language, normalize_response_language
from splitmind_ai.app.logging_utils import configure_logging, preview_text
from splitmind_ai.app.llm import create_chat_llm
from splitmind_ai.app.settings import PROJECT_ROOT, get_default_persona, load_settings
from splitmind_ai.personas.loader import list_personas
from splitmind_ai.ui.dashboard import build_current_dashboard, build_history_rows, build_turn_snapshot

logger = logging.getLogger(__name__)

UI_TEXT = {
    "en": {
        "app_title": "SplitMind-AI",
        "sidebar_title": "SplitMind-AI Research",
        "persona": "Persona",
        "show_trace": "Show trace",
        "vault_persistence": "Vault persistence",
        "response_language": "Response language",
        "ui_language": "UI language",
        "auto": "Auto",
        "japanese": "Japanese",
        "english": "English",
        "reset_session": "Reset Session",
        "user": "User",
        "session": "Session",
        "turns": "Turns",
        "current_summary": "Current Summary",
        "top_tension": "Top tension",
        "none": "none",
        "dominant_want": "Dominant want",
        "ego_move": "Ego move",
        "event": "Event",
        "trust": "Trust",
        "tension": "Tension",
        "tab_chat": "Chat",
        "tab_dashboard": "Dashboard",
        "send_message": "Send a message...",
        "thinking": "Thinking...",
        "error": "Error",
        "trace_turn": "Trace (turn {turn})",
        "raw_trace_json": "Raw trace JSON",
        "session_dashboard": "Session Dashboard",
        "dashboard_empty": "Start chatting to populate the session dashboard.",
        "conflict_flow": "Conflict Flow",
        "conflict_profile": "Conflict Profile",
        "relationship_over_time": "Relationship Over Time",
        "relationship_signals": "Relationship signals",
        "conflict_over_time": "Conflict Over Time",
        "conflict_signals": "Conflict signals",
        "surface_pacing_timeline": "Surface / Pacing Timeline",
        "surface_and_pacing": "Surface and pacing",
        "node_timing_over_time": "Node Timing Over Time",
        "node_timing": "Node timing",
        "appraisal_map": "Appraisal Map",
        "appraisal": "Appraisal",
        "fidelity_state": "Fidelity State",
        "conflict_summary": "Conflict Summary",
        "event_timeline": "Event Timeline",
        "expression_envelope": "Expression Envelope",
        "current_trace": "Current Trace",
        "top_unresolved_tensions": "Top Unresolved Tensions",
        "no_unresolved_tensions": "No unresolved tensions.",
        "memory_counts": "Memory Counts",
        "pacing_state": "Pacing State",
        "fidelity_verdict": "Fidelity Verdict",
        "latest_node_timing": "Latest Node Timing",
        "current_mood": "Current Mood",
        "top_target": "Top Target",
        "residue": "Residue",
        "current_turn_read": "Current Turn Read",
        "no_drive_flow": "No drive flow available yet.",
        "no_residue_profile": "No residue profile available.",
        "active_themes": "Active themes",
        "fidelity_warnings": "Fidelity warnings",
        "source": "Source",
        "intensity": "Intensity",
        "no_events_fired": "No events fired yet.",
        "turn_label": "Turn {turn}",
        "conflict_trace": "Conflict Trace",
        "expression_trace": "Expression Trace",
        "event_type": "Event",
        "valence": "Valence",
        "tension_target": "Tension target",
        "expression_length": "Expression length",
        "temperature": "Temperature",
        "directness": "Directness",
        "fidelity_passed": "Fidelity passed",
        "move_fidelity": "Move fidelity",
        "warnings": "Warnings",
        "recent_conflict_summaries": "Recent conflict summaries: {count}",
        "timing": "Timing",
        "ms": "ms",
        "yes": "yes",
        "no": "no",
        "unknown": "unknown",
        "no_response": "(no response)",
        "turn_axis": "turn",
        "score_axis": "score",
    },
    "ja": {
        "app_title": "SplitMind-AI",
        "sidebar_title": "SplitMind-AI Research",
        "persona": "ペルソナ",
        "show_trace": "トレースを表示",
        "vault_persistence": "Vault を保持",
        "response_language": "応答言語",
        "ui_language": "表示言語",
        "auto": "自動",
        "japanese": "日本語",
        "english": "English",
        "reset_session": "セッションをリセット",
        "user": "ユーザー",
        "session": "セッション",
        "turns": "ターン数",
        "current_summary": "現在の要約",
        "top_tension": "主要な緊張",
        "none": "なし",
        "dominant_want": "主な欲求",
        "ego_move": "エゴの動き",
        "event": "イベント",
        "trust": "信頼",
        "tension": "緊張",
        "tab_chat": "チャット",
        "tab_dashboard": "ダッシュボード",
        "send_message": "メッセージを送信...",
        "thinking": "考え中...",
        "error": "エラー",
        "trace_turn": "トレース（{turn}ターン目）",
        "raw_trace_json": "生のトレース JSON",
        "session_dashboard": "セッションダッシュボード",
        "dashboard_empty": "チャットを開始するとダッシュボードが表示されます。",
        "conflict_flow": "対立フロー",
        "conflict_profile": "対立プロファイル",
        "relationship_over_time": "関係性の推移",
        "relationship_signals": "関係性シグナル",
        "conflict_over_time": "対立の推移",
        "conflict_signals": "対立シグナル",
        "surface_pacing_timeline": "表層反応 / ペーシングの推移",
        "surface_and_pacing": "表層反応とペーシング",
        "node_timing_over_time": "ノード処理時間の推移",
        "node_timing": "ノード処理時間",
        "appraisal_map": "評価マップ",
        "appraisal": "評価",
        "fidelity_state": "忠実性の状態",
        "conflict_summary": "対立サマリー",
        "event_timeline": "イベントの履歴",
        "expression_envelope": "表現エンベロープ",
        "current_trace": "現在のトレース",
        "top_unresolved_tensions": "未解消の主要テンション",
        "no_unresolved_tensions": "未解消のテンションはありません。",
        "memory_counts": "メモリ件数",
        "pacing_state": "ペーシング状態",
        "fidelity_verdict": "忠実性判定",
        "latest_node_timing": "最新ノード処理時間",
        "current_mood": "現在のムード",
        "top_target": "主要ターゲット",
        "residue": "残滓",
        "current_turn_read": "現在ターンの読み取り",
        "no_drive_flow": "まだドライブフローはありません。",
        "no_residue_profile": "残滓プロファイルはまだありません。",
        "active_themes": "アクティブテーマ",
        "fidelity_warnings": "忠実性の警告",
        "source": "ソース",
        "intensity": "強度",
        "no_events_fired": "まだイベントは発火していません。",
        "turn_label": "{turn}ターン目",
        "conflict_trace": "対立トレース",
        "expression_trace": "表現トレース",
        "event_type": "イベント",
        "valence": "感情価",
        "tension_target": "テンションの対象",
        "expression_length": "発話の長さ",
        "temperature": "温度感",
        "directness": "直接性",
        "fidelity_passed": "忠実性チェック",
        "move_fidelity": "動きの忠実性",
        "warnings": "警告",
        "recent_conflict_summaries": "最近の対立サマリー: {count}",
        "timing": "処理時間",
        "ms": "ms",
        "yes": "はい",
        "no": "いいえ",
        "unknown": "不明",
        "no_response": "（応答なし）",
        "turn_axis": "ターン",
        "score_axis": "スコア",
    },
}

FIELD_LABELS = {
    "length": "Length",
    "temperature": "Temperature",
    "directness": "Directness",
    "relationship_stage": "Stage",
    "commitment_readiness": "Readiness",
    "repair_depth": "Repair depth",
    "escalation_allowed": "Escalation",
    "passed": "Passed",
    "move_fidelity": "Move fidelity",
    "warnings": "Warnings",
    "dominant_want": "Dominant want",
    "social_move": "Social move",
    "residue": "Residue",
    "emotional_memories": "Emotional memories",
    "semantic_preferences": "Semantic preferences",
    "active_themes": "Active themes",
    "event_type": "Event type",
    "target_of_tension": "Target tension",
    "visible_emotion": "Residue",
    "temperature_expression": "Expression temp",
    "fidelity_pass": "Fidelity",
}

LABEL_TRANSLATIONS = {
    "ja": {
        "Length": "長さ",
        "Temperature": "温度感",
        "Directness": "直接性",
        "Stage": "段階",
        "Readiness": "準備度",
        "Repair depth": "修復の深さ",
        "Escalation": "進展許可",
        "Passed": "通過",
        "Move fidelity": "動きの忠実性",
        "Warnings": "警告",
        "Dominant want": "主な欲求",
        "Social move": "社会的な動き",
        "Residue": "残滓",
        "Emotional memories": "感情メモリ",
        "Semantic preferences": "意味記憶",
        "Active themes": "アクティブテーマ",
        "Event type": "イベント種別",
        "Target tension": "テンション対象",
        "Expression temp": "表現温度",
        "Fidelity": "忠実性",
        "Id Intensity": "イドの強さ",
        "Superego Pressure": "超自我の圧力",
        "Residue Intensity": "残滓の強さ",
        "Closure": "終止感",
        "Appraisal": "評価",
        "Tension": "テンション",
        "Superego": "超自我",
        "Ego Move": "エゴの動き",
        "Expression": "表現",
        "Relationship": "関係性",
    }
}

VALUE_TEXT = {
    "ja": {
        "none": "なし",
        "unknown": "不明",
        "yes": "はい",
        "no": "いいえ",
        "pass": "合格",
        "warn": "要確認",
        "clear": "制約なし",
        "contained": "抑制中",
        "hold state": "保留状態",
        "unfixed": "未確定",
        "untracked": "未追跡",
        "short": "短め",
        "medium": "中くらい",
        "long": "長め",
        "cool_warm": "クール寄りで温かい",
        "cool": "クール",
        "warm": "温かい",
        "ambiguity": "曖昧さ",
        "closeness": "親密さ",
        "pride": "プライド",
        "jealousy": "嫉妬",
        "warming": "距離が温まりつつある",
        "unfamiliar": "まだ距離がある",
        "move_closer": "近づきたい",
        "receive_without_chasing": "追わずに受け取る",
        "accept_but_hold": "受け取りつつ保留",
        "allow_dependence_but_reframe": "甘えを許しつつ枠を保つ",
        "acknowledge_without_opening": "認めつつ開きすぎない",
        "interest_under_restraint": "興味はあるが抑えている",
        "repair_offer": "修復の申し出",
        "reassurance": "安心化",
        "pleased_but_guarded": "うれしいが警戒している",
        "composed_and_proud": "冷静で誇りを守りたい",
    }
}


def _resolve_default_ui_language(environ: MutableMapping[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    language_hint = (env.get("LANG") or env.get("LC_ALL") or "").lower()
    normalized = normalize_response_language(language_hint.split(".", 1)[0])
    if normalized in {"ja", "en"}:
        return normalized
    if language_hint.startswith("ja"):
        return "ja"
    return "en"


def _t(ui_language: str, key: str, **kwargs: Any) -> str:
    table = UI_TEXT.get(ui_language, UI_TEXT["en"])
    template = table.get(key, UI_TEXT["en"].get(key, key))
    return template.format(**kwargs)


def _humanize_code(value: Any, ui_language: str) -> str:
    if value is None:
        return _t(ui_language, "none")
    if isinstance(value, bool):
        return _t(ui_language, "yes") if value else _t(ui_language, "no")

    text = str(value).strip()
    if not text:
        return _t(ui_language, "none")

    translated = VALUE_TEXT.get(ui_language, {}).get(text)
    if translated:
        return translated
    if text in {"yes", "no", "unknown", "none"}:
        return _t(ui_language, text)
    if "_" in text and " " not in text:
        return text.replace("_", " ")
    return text


def _translate_label(label: str, ui_language: str) -> str:
    return LABEL_TRANSLATIONS.get(ui_language, {}).get(label, label)


def _row_label(row: dict[str, Any], ui_language: str) -> str:
    key = str(row.get("key") or "")
    if key:
        base = FIELD_LABELS.get(key, key.replace("_", " ").title())
    else:
        base = str(row.get("label") or "")
    return _translate_label(base, ui_language)


def _format_row_value(value: Any, ui_language: str, *, key: str = "") -> str:
    if key in {"directness", "commitment_readiness", "repair_depth", "move_fidelity"}:
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "0.00"
    return _humanize_code(value, ui_language)


def _safe_html(value: Any) -> str:
    return escape(str(value), quote=True)

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
    if "ui_language" not in target:
        target["ui_language"] = _resolve_default_ui_language()


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
    runtime = getattr(settings, "runtime", None)
    return (
        settings.llm.provider,
        settings.llm.model,
        settings.llm.azure_deployment,
        settings.llm.api_version,
        getattr(runtime, "max_iterations", None),
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
        max_iterations=getattr(getattr(settings, "runtime", None), "max_iterations", None),
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

    for slice_name in (
        "persona",
        "relationship_state",
        "mood",
        "memory",
        "working_memory",
    ):
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

def _render_sidebar() -> tuple[str, bool, str | None, str, str]:
    """Render sidebar controls and return persona, trace mode, vault path, and language modes."""
    ui_language = st.session_state.get("ui_language", _resolve_default_ui_language())
    st.sidebar.title(_t(ui_language, "sidebar_title"))

    # Persona selector
    available = list_personas()
    settings = load_settings()
    default_persona = get_default_persona(settings)
    default_idx = available.index(default_persona) if default_persona in available else 0
    persona_name = st.sidebar.selectbox(_t(ui_language, "persona"), available, index=default_idx)

    # Trace mode
    trace_mode = st.sidebar.toggle(_t(ui_language, "show_trace"), value=True)

    # Vault
    vault_enabled = st.sidebar.toggle(
        _t(ui_language, "vault_persistence"),
        value=settings.vault.enabled,
    )
    vault_path = str((PROJECT_ROOT / settings.vault.path).resolve()) if vault_enabled else None

    language_options = {
        _t(ui_language, "auto"): "auto",
        _t(ui_language, "japanese"): "ja",
        _t(ui_language, "english"): "en",
    }
    language_labels = list(language_options.keys())
    current_language = st.session_state.get("response_language", "auto")
    default_language = next(
        (label for label, value in language_options.items() if value == current_language),
        "Auto",
    )
    selected_label = st.sidebar.selectbox(
        _t(ui_language, "response_language"),
        language_labels,
        index=language_labels.index(default_language),
    )
    st.session_state["response_language"] = language_options[selected_label]

    ui_language_options = {
        _t(ui_language, "japanese"): "ja",
        _t(ui_language, "english"): "en",
    }
    ui_language_labels = list(ui_language_options.keys())
    selected_ui_label = st.sidebar.selectbox(
        _t(ui_language, "ui_language"),
        ui_language_labels,
        index=0 if st.session_state.get("ui_language") == "ja" else 1,
    )
    st.session_state["ui_language"] = ui_language_options[selected_ui_label]
    ui_language = st.session_state["ui_language"]

    # Reset session
    if st.sidebar.button(_t(ui_language, "reset_session")):
        _reset_session_state()
        st.rerun()

    # Session info
    st.sidebar.divider()
    st.sidebar.caption(f"{_t(ui_language, 'user')}: {st.session_state.user_id}")
    st.sidebar.caption(f"{_t(ui_language, 'session')}: {st.session_state.session_id}")
    st.sidebar.caption(f"{_t(ui_language, 'turns')}: {st.session_state.turn_count}")

    return (
        persona_name,
        trace_mode,
        vault_path,
        st.session_state["response_language"],
        ui_language,
    )


# ---------------------------------------------------------------------------
# State display
# ---------------------------------------------------------------------------

def _render_state_panel(state: dict[str, Any], ui_language: str) -> None:
    """Render minimal session summary in the sidebar."""
    relationship_state = state.get("relationship_state", {}) or {}
    conflict_state = state.get("conflict_state", {}) or {}
    appraisal = state.get("appraisal", {}) or {}
    durable = relationship_state.get("durable", {}) or {}
    ephemeral = relationship_state.get("ephemeral", {}) or {}
    if not durable and not conflict_state and not appraisal:
        return

    st.sidebar.divider()
    st.sidebar.subheader(_t(ui_language, "current_summary"))

    tensions = list(durable.get("unresolved_tension_summary", []) or [])
    if tensions:
        st.sidebar.caption(
            f"{_t(ui_language, 'top_tension')}: {_humanize_code(tensions[0], ui_language)}"
        )
    else:
        st.sidebar.caption(f"{_t(ui_language, 'top_tension')}: {_t(ui_language, 'none')}")

    id_impulse = (conflict_state.get("id_impulse") or {})
    if id_impulse:
        target = id_impulse.get("target") or ""
        target_suffix = f" -> {_humanize_code(target, ui_language)}" if target else ""
        st.sidebar.caption(
            (
                f"{_t(ui_language, 'dominant_want')}: "
                f"{_humanize_code(id_impulse.get('dominant_want', '?'), ui_language)} "
                f"({float(id_impulse.get('intensity', 0.0)):.2f}){target_suffix}"
            )
        )
    else:
        st.sidebar.caption(f"{_t(ui_language, 'dominant_want')}: {_t(ui_language, 'none')}")

    social_move = ((conflict_state.get("ego_move") or {}).get("social_move"))
    if social_move:
        st.sidebar.caption(f"{_t(ui_language, 'ego_move')}: {_humanize_code(social_move, ui_language)}")
    if appraisal.get("event_type"):
        st.sidebar.caption(
            f"{_t(ui_language, 'event')}: {_humanize_code(appraisal.get('event_type'), ui_language)}"
        )
    if durable or ephemeral:
        st.sidebar.caption(
            (
                f"{_t(ui_language, 'trust')}: {float(durable.get('trust', 0.0)):.2f} | "
                f"{_t(ui_language, 'tension')}: {float(ephemeral.get('tension', 0.0)):.2f}"
            )
        )


def _inject_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #fffdf9 0%, #f7efe6 100%);
            border: 1px solid rgba(18, 53, 91, 0.08);
            border-radius: 18px;
            padding: 0.4rem 0.2rem;
            box-shadow: 0 8px 22px rgba(18, 53, 91, 0.06);
        }
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
            margin-bottom: 0.9rem;
        }
        .sm-mini-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.6rem;
        }
        .sm-mini-card {
            padding: 0.75rem 0.85rem;
            border-radius: 14px;
            background: #fffdf9;
            border: 1px solid rgba(18, 53, 91, 0.08);
            min-width: 0;
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
            overflow-wrap: anywhere;
        }
        .sm-badge-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.2rem 0 0.8rem 0;
        }
        .sm-badge {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: #efe4d6;
            color: #12355b;
            font-size: 0.85rem;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .sm-detail-grid {
            display: grid;
            gap: 0.65rem;
        }
        .sm-detail-card {
            padding: 0.85rem 0.95rem;
            border-radius: 16px;
            background: linear-gradient(180deg, #fffdf9 0%, #f7efe6 100%);
            border: 1px solid rgba(18, 53, 91, 0.08);
            box-shadow: 0 8px 20px rgba(18, 53, 91, 0.05);
        }
        .sm-detail-label {
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7f6a53;
            margin-bottom: 0.2rem;
        }
        .sm-detail-value {
            font-size: 1rem;
            line-height: 1.4;
            color: #12355b;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        .sm-detail-meta {
            margin-top: 0.25rem;
            font-size: 0.82rem;
            color: #5a6473;
            overflow-wrap: anywhere;
        }
        .sm-section-title {
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7f6a53;
            margin: 0 0 0.45rem 0;
        }
        @media (max-width: 1100px) {
            .sm-mini-grid {
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_detail_cards(
    rows: list[dict[str, Any]],
    ui_language: str,
    *,
    show_target: bool = False,
) -> None:
    if not rows:
        st.caption(_t(ui_language, "none"))
        return

    cards = []
    for row in rows:
        key = str(row.get("key") or "")
        label = _safe_html(_row_label(row, ui_language))
        value = _safe_html(_format_row_value(row.get("value"), ui_language, key=key))
        meta = ""
        if show_target and row.get("target"):
            meta = (
                f'<div class="sm-detail-meta">{_safe_html(_humanize_code(row["target"], ui_language))}</div>'
            )
        cards.append(
            '<div class="sm-detail-card">'
            f'<div class="sm-detail-label">{label}</div>'
            f'<div class="sm-detail-value">{value}</div>'
            f"{meta}"
            "</div>"
        )
    st.markdown(f'<div class="sm-detail-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_tension_cards(tensions: list[dict[str, Any]], ui_language: str) -> None:
    if not tensions:
        st.caption(_t(ui_language, "no_unresolved_tensions"))
        return

    cards = []
    for tension in tensions:
        source = ""
        if tension.get("source"):
            source = (
                f'<div class="sm-detail-meta">{_safe_html(_t(ui_language, "source"))}: '
                f'{_safe_html(tension["source"])}</div>'
            )
        cards.append(
            '<div class="sm-detail-card">'
            f'<div class="sm-detail-label">{_safe_html(_t(ui_language, "intensity"))}</div>'
            f'<div class="sm-detail-value">{_safe_html(_humanize_code(tension.get("theme"), ui_language))} · '
            f'{float(tension.get("intensity", 0.0)):.2f}</div>'
            f"{source}"
            "</div>"
        )
    st.markdown(f'<div class="sm-detail-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_story_flow(
    story_steps: list[dict[str, str]],
    drive_story: str,
    ui_language: str,
) -> None:
    st.markdown(
        (
            '<div class="sm-story">'
            f'<div class="sm-story-label">{_safe_html(_t(ui_language, "current_turn_read"))}</div>'
            f'<div class="sm-story-body">{_safe_html(drive_story)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if not story_steps:
        st.caption(_t(ui_language, "no_drive_flow"))
        return

    cards = []
    for step in story_steps:
        cards.append(
            '<div class="sm-flow-card">'
            f'<div class="sm-flow-stage">{_safe_html(_translate_label(step.get("stage", ""), ui_language))}</div>'
            f'<div class="sm-flow-value">{_safe_html(_humanize_code(step.get("value", ""), ui_language))}</div>'
            f'<div class="sm-flow-note">{_safe_html(_humanize_code(step.get("note", ""), ui_language))}</div>'
            "</div>"
        )
    st.markdown(f'<div class="sm-flow">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_pressure_panel(residue_rows: list[dict[str, Any]], ui_language: str) -> None:
    if not residue_rows:
        st.caption(_t(ui_language, "no_residue_profile"))
        return

    notes = {
        "en": {
            "id_intensity": "How much drive is active right now.",
            "superego_pressure": "How much pressure is being held back.",
            "residue_intensity": "How much this turn carries forward.",
            "directness": "How directly the response can move.",
            "closure": "How complete the response is allowed to feel.",
        },
        "ja": {
            "id_intensity": "いまどれだけ欲求が動いているか。",
            "superego_pressure": "どれだけ抑制圧がかかっているか。",
            "residue_intensity": "このターンにどれだけ残滓が残るか。",
            "directness": "どれだけ直接的に動けるか。",
            "closure": "どれだけ言い切れるか。",
        },
    }
    parts = []
    for row in residue_rows:
        color = _meter_color(str(row.get("tone", "")))
        value = float(row.get("value", 0.0))
        parts.append(
            '<div class="sm-meter">'
            '<div class="sm-meter-header">'
            f'<span>{_safe_html(_translate_label(row.get("label", ""), ui_language))}</span>'
            f"<strong>{value:.2f}</strong>"
            "</div>"
            '<div class="sm-meter-track">'
            f'<div class="sm-meter-fill" style="width:{value * 100:.0f}%;background:{color};"></div>'
            "</div>"
            f'<div class="sm-meter-note">{_safe_html(notes[ui_language].get(row.get("key", ""), ""))}</div>'
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


def _render_surface_panel(
    current: dict[str, Any],
    active_themes: list[str],
    ui_language: str,
) -> None:
    appraisal = current.get("appraisal", {}) or {}
    conflict = current.get("conflict", {}) or {}
    expression = current.get("expression", {}) or {}
    pacing = current.get("pacing", {}) or {}
    fidelity = current.get("fidelity", {}) or {}
    blocked = ", ".join(_humanize_code(item, ui_language) for item in (conflict.get("forbidden_moves", []) or []))
    blocked = blocked or _t(ui_language, "none")

    cards = [
        (_translate_label("Event type", ui_language), appraisal.get("event_type") or "unknown"),
        (_translate_label("Target tension", ui_language), appraisal.get("target_of_tension") or "unknown"),
        (_t(ui_language, "ego_move"), conflict.get("social_move") or "contained"),
        (_translate_label("Residue", ui_language), conflict.get("visible_emotion") or "contained"),
        (_translate_label("Relationship", ui_language), pacing.get("relationship_stage") or "untracked"),
        (_translate_label("Expression temp", ui_language), expression.get("temperature") or "unknown"),
        ("Forbidden moves" if ui_language == "en" else "禁止された動き", blocked),
        (_translate_label("Fidelity", ui_language), "pass" if fidelity.get("passed") else "warn"),
    ]
    html_cards = []
    for label, value in cards:
        html_cards.append(
            '<div class="sm-mini-card">'
            f'<div class="sm-mini-label">{_safe_html(label)}</div>'
            f'<div class="sm-mini-value">{_safe_html(_humanize_code(value, ui_language))}</div>'
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
        st.markdown(f'<div class="sm-section-title">{_safe_html(_t(ui_language, "active_themes"))}</div>', unsafe_allow_html=True)
        st.markdown(_format_badges(active_themes, ui_language), unsafe_allow_html=True)
    warnings = list(fidelity.get("warnings", []) or [])
    if warnings:
        st.markdown(f'<div class="sm-section-title">{_safe_html(_t(ui_language, "fidelity_warnings"))}</div>', unsafe_allow_html=True)
        st.markdown(_format_badges(warnings, ui_language), unsafe_allow_html=True)


def _meter_color(tone: str) -> str:
    return {
        "heat": "linear-gradient(90deg, #d17a22 0%, #b23a48 100%)",
        "risk": "linear-gradient(90deg, #b23a48 0%, #8f1d2c 100%)",
        "carry": "linear-gradient(90deg, #3c6e71 0%, #12355b 100%)",
        "block": "linear-gradient(90deg, #6a4c93 0%, #355c7d 100%)",
        "release": "linear-gradient(90deg, #6b8f71 0%, #3c6e71 100%)",
    }.get(tone, "#d17a22")


def _render_dashboard(turn_snapshots: list[dict[str, Any]], ui_language: str) -> None:
    st.subheader(_t(ui_language, "session_dashboard"))
    if not turn_snapshots:
        st.info(_t(ui_language, "dashboard_empty"))
        return

    _inject_dashboard_styles()
    dashboard = build_current_dashboard(turn_snapshots)
    history = build_history_rows(turn_snapshots)
    current = dashboard["current"] or {}

    _render_kpi_cards(current, dashboard["turns"], ui_language)

    col1, col2 = st.columns((7, 5))
    with col1:
        st.caption(_t(ui_language, "conflict_flow"))
        _render_story_flow(dashboard["story_steps"], dashboard["conflict_story"], ui_language)
    with col2:
        st.caption(_t(ui_language, "conflict_profile"))
        _render_pressure_panel(dashboard["residue_rows"], ui_language)

    col1, col2 = st.columns(2)
    with col1:
        st.caption(_t(ui_language, "relationship_over_time"))
        st.plotly_chart(
            _make_multi_line_chart(
                history["relationship"],
                title=_t(ui_language, "relationship_signals"),
                yaxis_title=_t(ui_language, "score_axis"),
                ui_language=ui_language,
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
    with col2:
        st.caption(_t(ui_language, "conflict_over_time"))
        st.plotly_chart(
            _make_multi_line_chart(
                history["affect"],
                title=_t(ui_language, "conflict_signals"),
                yaxis_title=_t(ui_language, "score_axis"),
                ui_language=ui_language,
            ),
            width="stretch",
            config={"displayModeBar": False},
        )

    if history["surface"]:
        st.caption(_t(ui_language, "surface_pacing_timeline"))
        st.plotly_chart(
            _make_state_timeline(history["surface"], ui_language=ui_language),
            width="stretch",
            config={"displayModeBar": False},
        )

    if history["timing"]:
        st.caption(_t(ui_language, "node_timing_over_time"))
        st.plotly_chart(
            _make_timing_chart(history["timing"], ui_language=ui_language),
            width="stretch",
            config={"displayModeBar": False},
        )

    col1, col2 = st.columns(2)
    with col1:
        st.caption(_t(ui_language, "appraisal_map"))
        st.plotly_chart(
            _make_radar_chart(
                dashboard["appraisal_radar"],
                title=_t(ui_language, "appraisal"),
                ui_language=ui_language,
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
    with col2:
        st.caption(_t(ui_language, "fidelity_state"))
        _render_detail_cards(dashboard["fidelity_rows"], ui_language)

    col1, col2 = st.columns((7, 5))
    with col1:
        st.caption(_t(ui_language, "conflict_summary"))
        _render_detail_cards(dashboard["conflict_rows"], ui_language, show_target=True)
    with col2:
        st.caption(_t(ui_language, "event_timeline"))
        _render_event_groups(dashboard["event_groups"], ui_language)

    col1, col2 = st.columns((7, 5))
    with col1:
        st.caption(_t(ui_language, "current_trace"))
        _render_surface_panel(current, dashboard["active_themes"], ui_language)
        st.caption(_t(ui_language, "expression_envelope"))
        _render_detail_cards(dashboard["expression_rows"], ui_language)
    with col2:
        st.caption(_t(ui_language, "top_unresolved_tensions"))
        _render_tension_cards(dashboard["unresolved_tensions"], ui_language)

        st.caption(_t(ui_language, "memory_counts"))
        counts = dashboard["memory_counts"]
        _render_detail_cards(
            [
                {"key": "emotional_memories", "value": counts.get("emotional_memories", 0)},
                {"key": "semantic_preferences", "value": counts.get("semantic_preferences", 0)},
                {"key": "active_themes", "value": counts.get("active_themes", 0)},
            ],
            ui_language,
        )

        st.caption(_t(ui_language, "pacing_state"))
        _render_detail_cards(dashboard["pacing_rows"], ui_language)

        st.caption(_t(ui_language, "fidelity_verdict"))
        _render_detail_cards(dashboard["fidelity_rows"], ui_language)

    timing_rows = dashboard["timing_rows"]
    if timing_rows:
        st.caption(_t(ui_language, "latest_node_timing"))
        _render_detail_cards(
            [
                {
                    "label": row["label"].replace("_", " "),
                    "value": f"{row['value']:.2f} {_t(ui_language, 'ms')}",
                }
                for row in timing_rows
            ],
            ui_language,
        )


def _render_kpi_cards(current: dict[str, Any], turns: int, ui_language: str) -> None:
    mood = (current.get("mood", {}) or {}).get("base_mood") or "unknown"
    conflict = current.get("conflict", {}) or {}
    primary_drive = conflict.get("dominant_want") or "unknown"
    top_target = conflict.get("target") or "none"
    selected_mode = conflict.get("social_move") or "unknown"
    leakage = conflict.get("residue_intensity", 0.0)

    cards = st.columns(6)
    cards[0].metric(_t(ui_language, "current_mood"), _humanize_code(mood, ui_language))
    cards[1].metric(_t(ui_language, "dominant_want"), _humanize_code(primary_drive, ui_language))
    cards[2].metric(_t(ui_language, "top_target"), _humanize_code(top_target, ui_language))
    cards[3].metric(_t(ui_language, "ego_move"), _humanize_code(selected_mode, ui_language))
    cards[4].metric(_t(ui_language, "residue"), f"{float(leakage):.2f}")
    cards[5].metric(_t(ui_language, "turns"), str(turns))


def _make_multi_line_chart(
    rows: list[dict[str, Any]],
    *,
    title: str,
    yaxis_title: str,
    ui_language: str,
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
            name=_humanize_code(metric, ui_language),
            line={"width": 3, "color": palette[index % len(palette)]},
        ))

    figure.update_layout(
        title=title,
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F3EE",
        yaxis={"range": [0, 1], "title": yaxis_title},
        xaxis={"title": _t(ui_language, "turn_axis"), "dtick": 1},
        legend={"orientation": "h", "y": -0.2},
    )
    return figure


def _make_radar_chart(rows: list[dict[str, Any]], *, title: str, ui_language: str):
    import plotly.graph_objects as go

    axes = [_humanize_code(row["axis"], ui_language) for row in rows]
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
            y=[
                (
                    f"{row['label']} [{row.get('surface_posture')}]"
                    if row.get("surface_posture")
                    else row["label"]
                )
                for row in ordered
            ],
            orientation="h",
            marker={"color": "#D17A22"},
            text=[
                f"{row['score']:.2f} | risk {float(row.get('pacing_risk', 0.0)):.2f}"
                for row in ordered
            ],
            customdata=[
                ", ".join(row.get("critic_flags", []) or []) or "none"
                for row in ordered
            ],
            hovertemplate=(
                "score=%{x:.2f}<br>critic=%{customdata}<extra></extra>"
            ),
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


def _make_state_timeline(rows: list[dict[str, Any]], *, ui_language: str):
    import plotly.graph_objects as go

    figure = go.Figure()
    metric_names = list(dict.fromkeys(row["metric"] for row in rows))
    palette = {
        "surface_posture": "#D17A22",
        "relationship_stage": "#12355B",
    }
    for metric in metric_names:
        metric_rows = [row for row in rows if row["metric"] == metric]
        figure.add_trace(go.Scatter(
            x=[row["turn"] for row in metric_rows],
            y=[row["value"] for row in metric_rows],
            mode="lines+markers",
            name=_humanize_code(metric, ui_language),
            line={"width": 3, "color": palette.get(metric, "#3C6E71")},
        ))

    figure.update_layout(
        title=_t(ui_language, "surface_and_pacing"),
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F3EE",
        xaxis={"title": _t(ui_language, "turn_axis"), "dtick": 1},
        yaxis={"title": ""},
        legend={"orientation": "h", "y": -0.25},
    )
    return figure


def _make_timing_chart(rows: list[dict[str, Any]], *, ui_language: str):
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
            name=_humanize_code(metric, ui_language),
            line={"width": 3, "color": palette[index % len(palette)]},
        ))

    figure.update_layout(
        title=_t(ui_language, "node_timing"),
        margin={"l": 20, "r": 20, "t": 48, "b": 20},
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F7F3EE",
        yaxis={"title": _t(ui_language, "ms")},
        xaxis={"title": _t(ui_language, "turn_axis"), "dtick": 1},
        legend={"orientation": "h", "y": -0.2},
    )
    return figure


def _render_event_groups(event_groups: list[dict[str, Any]], ui_language: str) -> None:
    if not event_groups:
        st.caption(_t(ui_language, "no_events_fired"))
        return

    for group in event_groups:
        st.markdown(f"**{_t(ui_language, 'turn_label', turn=group['turn'])}**")
        st.markdown(
            _format_badges(group["events"], ui_language),
            unsafe_allow_html=True,
        )


def _format_badges(items: list[str], ui_language: str) -> str:
    if not items:
        return ""
    badges = []
    for item in items:
        badges.append(
            f'<span class="sm-badge">{_safe_html(_humanize_code(item, ui_language))}</span>'
        )
    return f'<div class="sm-badge-list">{"".join(badges)}</div>'


# ---------------------------------------------------------------------------
# Trace display
# ---------------------------------------------------------------------------

def _render_trace(trace_data: dict[str, Any], ui_language: str) -> None:
    """Render trace information for a single turn."""
    appraisal = trace_data.get("appraisal", {})
    conflict = trace_data.get("conflict_engine", {})
    expression = trace_data.get("expression_realizer", {})
    fidelity = trace_data.get("fidelity_gate", {})
    commit = trace_data.get("memory_commit", {})

    col1, col2 = st.columns(2)

    with col1:
        if appraisal or conflict:
            st.caption(_t(ui_language, "conflict_trace"))
            st.markdown(f"- **{_t(ui_language, 'event_type')}**: {_humanize_code(appraisal.get('event_type', '?'), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'valence')}**: {_humanize_code(appraisal.get('valence', '?'), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'tension_target')}**: {_humanize_code(appraisal.get('target_of_tension', '?'), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'dominant_want')}**: {_humanize_code(((conflict.get('id_impulse', {}) or {}).get('dominant_want') or '?'), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'ego_move')}**: {_humanize_code(((conflict.get('ego_move', {}) or {}).get('social_move') or '?'), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'residue')}**: {_humanize_code(((conflict.get('residue', {}) or {}).get('visible_emotion') or '?'), ui_language)}")

    with col2:
        if expression or fidelity:
            st.caption(_t(ui_language, "expression_trace"))
            envelope = expression.get("expression_envelope", {}) or {}
            st.markdown(f"- **{_t(ui_language, 'expression_length')}**: {_humanize_code(envelope.get('length', '?'), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'temperature')}**: {_humanize_code(envelope.get('temperature', '?'), ui_language)}")
            st.markdown(f"- **Directness**: {envelope.get('directness', '?')}")
            st.markdown(f"- **{_t(ui_language, 'fidelity_passed')}**: {_humanize_code(fidelity.get('passed', False), ui_language)}")
            st.markdown(f"- **{_t(ui_language, 'move_fidelity')}**: {fidelity.get('move_fidelity', '?')}")
            warnings = list(fidelity.get("warnings", []) or [])
            if warnings:
                st.markdown(
                    f"- **{_t(ui_language, 'warnings')}**: "
                    f"{', '.join(_humanize_code(item, ui_language) for item in warnings[:2])}"
                )

    if commit:
        recent = list(commit.get("recent_conflict_summaries", []) or [])
        if recent:
            st.caption(_t(ui_language, "recent_conflict_summaries", count=len(recent)))

    timing_rows = _collect_trace_timings(trace_data)
    if timing_rows:
        st.caption(_t(ui_language, "timing"))
        for label, value in timing_rows:
            st.markdown(f"- **{_humanize_code(label, ui_language)}**: {value:.2f} {_t(ui_language, 'ms')}")

    # Downloadable raw JSON
    with st.expander(_t(ui_language, "raw_trace_json")):
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


def _render_chat_history(*, show_trace: bool, ui_language: str) -> None:
    trace_indices = _assistant_trace_indices(st.session_state.messages)
    for msg, trace_idx in zip(st.session_state.messages, trace_indices):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
        if show_trace and trace_idx is not None and trace_idx < len(st.session_state.traces):
            with st.expander(_t(ui_language, "trace_turn", turn=trace_idx + 1), expanded=False):
                _render_trace(st.session_state.traces[trace_idx], ui_language)


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
    persona_name, trace_mode, vault_path, response_language, ui_language = _render_sidebar()
    _render_state_panel(st.session_state.latest_state, ui_language)

    st.title(_t(ui_language, "app_title"))

    tabs = st.tabs([_t(ui_language, "tab_chat"), _t(ui_language, "tab_dashboard")])
    chat_tab = tabs[0]
    dashboard_tab = tabs[1]

    with chat_tab:
        _render_chat_history(show_trace=trace_mode, ui_language=ui_language)

        if user_input := st.chat_input(_t(ui_language, "send_message")):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)

            with st.spinner(_t(ui_language, "thinking")):
                try:
                    result = _run_turn(
                        user_input,
                        persona_name,
                        vault_path,
                        st.session_state.user_id,
                        response_language,
                    )
                except Exception as e:
                    st.error(f"{_t(ui_language, 'error')}: {e}")
                    return

            response = result.get("response", {})
            final_text = response.get("final_response_text", _t(ui_language, "no_response"))

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
                    _t(ui_language, "trace_turn", turn=st.session_state.turn_count),
                    expanded=True,
                ):
                    _render_trace(result.get("trace", {}), ui_language)

            st.rerun()

    with dashboard_tab:
        _render_dashboard(st.session_state.turn_snapshots, ui_language)


if __name__ == "__main__":
    main()
