"""MemoryCommitNode: rule-based state update + vault persistence."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.app.logging_utils import preview_text
from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.rules.state_updates import DEFAULT_RULES, run_full_update

logger = logging.getLogger(__name__)


class MemoryCommitNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="memory_commit",
        description="Deterministic state merge and vault persistence after memory interpretation",
        reads=[
            "request",
            "response",
            "trace",
            "relationship_state",
            "mood",
            "memory",
            "working_memory",
            "appraisal",
            "conflict_state",
            "drive_state",
            "memory_interpretation",
            "_internal",
        ],
        writes=["relationship_state", "mood", "memory", "working_memory", "trace", "_internal"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=40,
                when={"trace.memory_interpreter": True},
                llm_hint="Run after memory interpretation to persist deterministic state updates",
            ),
        ],
        is_terminal=True,
        icon="💾",
    )

    def __init__(
        self,
        rules: dict[str, dict[str, float]] | None = None,
        vault_store: VaultStore | None = None,
        **services: Any,
    ) -> None:
        super().__init__(**services)
        self._rules = rules or DEFAULT_RULES
        self._vault = vault_store

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        started_at = perf_counter()
        relationship_state = dict(inputs.get_slice("relationship_state"))
        mood = dict(inputs.get_slice("mood"))
        memory = dict(inputs.get_slice("memory"))
        working_memory = dict(inputs.get_slice("working_memory"))
        appraisal = inputs.get_slice("appraisal")
        conflict_state = inputs.get_slice("conflict_state")
        drive_state = inputs.get_slice("drive_state")
        memory_interpretation = inputs.get_slice("memory_interpretation")
        internal = inputs.get_slice("_internal")
        request = inputs.get_slice("request")
        response = inputs.get_slice("response")

        interpreted_event_flags = dict(memory_interpretation.get("event_flags", {}) or {})
        event_flags: dict[str, bool] = {
            **dict(internal.get("event_flags", {}) or {}),
            **interpreted_event_flags,
        }
        logger.debug(
            "memory_commit start user_id=%s ego_move=%s active_flags=%s response=%s",
            internal.get("session", {}).get("user_id", request.get("user_id", "default")),
            (conflict_state.get("ego_move") or {}).get("social_move"),
            [k for k, v in event_flags.items() if v],
            preview_text(response.get("final_response_text")),
        )

        # Delegate to centralized state update engine
        session_info = internal.get("session", {})
        interpreted_memory_candidates = None
        if "emotional_memories" in memory_interpretation or "semantic_preferences" in memory_interpretation:
            interpreted_memory_candidates = {
                "emotional_memories": list(memory_interpretation.get("emotional_memories", []) or []),
                "semantic_preferences": list(memory_interpretation.get("semantic_preferences", []) or []),
            }
        unresolved_tension_summary_override = None
        if "unresolved_tension_summary" in memory_interpretation:
            unresolved_tension_summary_override = list(
                memory_interpretation.get("unresolved_tension_summary", []) or []
            )
        result = run_full_update(
            relationship_state=relationship_state,
            mood=mood,
            event_flags=event_flags,
            appraisal=appraisal,
            conflict_state=conflict_state,
            request=request,
            response=response,
            rules=self._rules,
            session_id=session_info.get("session_id", ""),
            turn_number=internal.get("turn_count", 0),
            memory_candidates_override=interpreted_memory_candidates,
            unresolved_tension_summary_override=unresolved_tension_summary_override,
        )

        updated_relationship_state = result["relationship_state"]
        updated_mood = result["mood"]
        memory_candidates = _enrich_memory_candidates(
            memory_candidates=result["memory_candidates"],
            drive_state=drive_state,
            conflict_state=conflict_state,
        )
        updated_memory = _merge_memory_context(memory, memory_candidates)
        updated_working_memory = _merge_working_memory(
            working_memory=working_memory,
            relationship_state=updated_relationship_state,
            request=request,
            conflict_state=conflict_state,
            drive_state=drive_state,
            memory_candidates=memory_candidates,
            event_flags=event_flags,
            memory_interpretation=memory_interpretation,
        )

        # Persist to vault
        user_id = internal.get("session", {}).get("user_id", request.get("user_id", "default"))
        vault_committed = False

        if self._vault is not None:
            try:
                self._vault.commit_turn(
                    user_id=user_id,
                    relationship_state=updated_relationship_state,
                    mood=updated_mood,
                    memory_candidates=memory_candidates,
                )
                vault_committed = True
                logger.info("Vault commit successful for user=%s", user_id)
            except Exception:
                logger.warning("Vault commit failed, response still returned", exc_info=True)

        trace = {
            "memory_commit": {
                **result["trace"],
                "used_memory_interpretation": True,
                "interpreted_event_flags": sorted(k for k, v in interpreted_event_flags.items() if v),
                "vault_committed": vault_committed,
                "memory_commit_ms": round((perf_counter() - started_at) * 1000, 2),
            }
        }

        persistence = {
            "should_save": True,
            "vault_committed": vault_committed,
            "session_id": internal.get("session", {}).get("session_id", ""),
        }
        logger.debug(
            "memory_commit complete trust=%.2f tension=%.2f mood=%s vault_committed=%s",
            (updated_relationship_state.get("durable", {}) or {}).get("trust", 0.0),
            (updated_relationship_state.get("ephemeral", {}) or {}).get("tension", 0.0),
            updated_mood.get("base_mood"),
            vault_committed,
        )

        return NodeOutputs(
            relationship_state=updated_relationship_state,
            mood=updated_mood,
            memory=updated_memory,
            working_memory=updated_working_memory,
            trace=trace,
            _internal={"persistence": persistence, "status": "completed"},
        )


def _merge_memory_context(
    memory: dict[str, Any],
    memory_candidates: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    updated = {
        "session_summaries": list(memory.get("session_summaries", [])),
        "emotional_memories": list(memory.get("emotional_memories", [])),
        "semantic_preferences": list(memory.get("semantic_preferences", [])),
    }

    emotional_existing = updated["emotional_memories"]
    for candidate in reversed(memory_candidates.get("emotional_memories", [])):
        emotional_existing.insert(0, candidate)
    updated["emotional_memories"] = emotional_existing[:8]

    semantic_by_topic: dict[str, dict[str, Any]] = {}
    for pref in updated["semantic_preferences"]:
        topic = pref.get("topic")
        if topic:
            semantic_by_topic[topic] = pref
    for candidate in memory_candidates.get("semantic_preferences", []):
        topic = candidate.get("topic")
        if topic:
            semantic_by_topic[topic] = candidate
    updated["semantic_preferences"] = list(semantic_by_topic.values())[:8]

    return updated


def _merge_working_memory(
    *,
    working_memory: dict[str, Any],
    relationship_state: dict[str, Any],
    request: dict[str, Any],
    conflict_state: dict[str, Any],
    drive_state: dict[str, Any],
    memory_candidates: dict[str, list[dict[str, Any]]],
    event_flags: dict[str, bool],
    memory_interpretation: dict[str, Any],
) -> dict[str, Any]:
    updated = {
        "active_themes": list(working_memory.get("active_themes", [])),
        "salient_user_phrases": list(working_memory.get("salient_user_phrases", [])),
        "retrieved_memory_ids": list(working_memory.get("retrieved_memory_ids", [])),
        "unresolved_questions": list(working_memory.get("unresolved_questions", [])),
        "current_episode_summary": working_memory.get("current_episode_summary"),
        "recent_conflict_summaries": list(working_memory.get("recent_conflict_summaries", [])),
    }

    user_message = request.get("user_message", "")
    if user_message:
        updated["salient_user_phrases"] = [user_message[:120], *updated["salient_user_phrases"]][:5]

    interpreted_active_themes = list(memory_interpretation.get("active_themes", []) or [])
    if interpreted_active_themes:
        updated["active_themes"] = interpreted_active_themes[:6]
    else:
        updated["active_themes"] = _rank_active_themes(
            existing_themes=updated["active_themes"],
            relationship_state=relationship_state,
            conflict_state=conflict_state,
            drive_state=drive_state,
            memory_candidates=memory_candidates,
            event_flags=event_flags,
        )
    for candidate in memory_candidates.get("emotional_memories", []):
        session_id = candidate.get("session_id")
        turn_number = candidate.get("turn_number")
        if session_id:
            updated["retrieved_memory_ids"] = [
                f"{session_id}:{turn_number or 0}",
                *updated["retrieved_memory_ids"],
            ][:5]

    interpreted_episode_summary = memory_interpretation.get("current_episode_summary")
    if interpreted_episode_summary is not None:
        updated["current_episode_summary"] = str(interpreted_episode_summary)[:160] or None
    elif user_message:
        updated["current_episode_summary"] = user_message[:160]
    summary = memory_interpretation.get("recent_conflict_summary") or _build_conflict_summary(
        request=request,
        relationship_state=relationship_state,
        conflict_state=conflict_state,
    )
    if summary:
        updated["recent_conflict_summaries"] = [
            summary,
            *updated["recent_conflict_summaries"],
        ][:6]

    return updated


def _rank_active_themes(
    *,
    existing_themes: list[str],
    relationship_state: dict[str, Any],
    conflict_state: dict[str, Any],
    drive_state: dict[str, Any],
    memory_candidates: dict[str, list[dict[str, Any]]],
    event_flags: dict[str, bool],
) -> list[str]:
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}

    def add(theme: str | None, weight: float, order_hint: int) -> None:
        if not theme:
            return
        scores[theme] = scores.get(theme, 0.0) + weight
        first_seen.setdefault(theme, order_hint)

    for index, theme in enumerate(existing_themes):
        add(theme, max(0.03, 0.18 - (index * 0.03)), index)

    resolution_turn = (
        event_flags.get("reassurance_received") or event_flags.get("repair_attempt")
    )
    unresolved = (
        ((relationship_state.get("durable", {}) or {}).get("unresolved_tension_summary", []))
        or []
    )
    unresolved_theme_names = {item for item in unresolved if item}
    base_order = len(first_seen)

    for offset, theme in enumerate(unresolved):
        if resolution_turn:
            add(theme, 0.34, base_order + offset)
        else:
            add(theme, 0.42, base_order + offset)

    dominant_desire = (conflict_state.get("id_impulse") or {}).get("dominant_want")
    affective_pressure = max(
        float((conflict_state.get("id_impulse") or {}).get("intensity", 0.0) or 0.0),
        float((conflict_state.get("residue") or {}).get("intensity", 0.0) or 0.0),
    )
    if dominant_desire:
        dominant_weight = 0.45
        if affective_pressure >= 0.5:
            dominant_weight += 0.2
        if resolution_turn:
            dominant_weight += 0.1
        add(dominant_desire, dominant_weight, -1)

    for offset, drive in enumerate(drive_state.get("top_drives", []) or []):
        if not isinstance(drive, dict):
            continue
        add(drive.get("name"), 0.34 + (float(drive.get("carryover", 0.0) or 0.0) * 0.2), 20 + offset)
        add(drive.get("target"), 0.18, 40 + offset)

    for offset, candidate in enumerate(memory_candidates.get("emotional_memories", [])):
        if not isinstance(candidate, dict):
            continue
        add(candidate.get("trigger"), 0.28, 100 + offset)
        add(candidate.get("target"), 0.22, 110 + offset)
        add(candidate.get("wound"), 0.18, 120 + offset)
        add(candidate.get("blocked_action"), 0.16, 130 + offset)
        add(candidate.get("attempted_action"), 0.15, 135 + offset)
        add(candidate.get("residual_drive"), 0.24, 138 + offset)
        add(candidate.get("emotion"), 0.12, 140 + offset)

    if resolution_turn:
        for theme in list(scores):
            if theme in unresolved_theme_names:
                scores[theme] -= 0.08
            elif theme != dominant_desire:
                scores[theme] -= 0.12

    ranked = sorted(
        (
            (theme, score)
            for theme, score in scores.items()
            if score > 0.16
        ),
        key=lambda item: (-item[1], first_seen.get(item[0], 999)),
    )
    return [theme for theme, _score in ranked[:6]]


def _enrich_memory_candidates(
    *,
    memory_candidates: dict[str, list[dict[str, Any]]],
    drive_state: dict[str, Any],
    conflict_state: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    updated = {
        "emotional_memories": [dict(item) for item in memory_candidates.get("emotional_memories", [])],
        "semantic_preferences": [dict(item) for item in memory_candidates.get("semantic_preferences", [])],
    }
    top_drives = list(drive_state.get("top_drives", []) or [])
    primary_drive = top_drives[0] if top_drives else {}
    target = primary_drive.get("target") or (drive_state.get("drive_targets", {}) or {}).get(primary_drive.get("name"))
    attempted_action = (conflict_state.get("ego_move") or {}).get("social_move") or ""
    residual_drive = primary_drive.get("name") or ""

    for memory in updated["emotional_memories"]:
        memory.setdefault("target", target)
        memory.setdefault("attempted_action", attempted_action)
        memory.setdefault("residual_drive", residual_drive or memory.get("trigger", ""))

    return updated


def _build_conflict_summary(
    *,
    request: dict[str, Any],
    relationship_state: dict[str, Any],
    conflict_state: dict[str, Any],
) -> dict[str, Any] | None:
    ego_move = str((conflict_state.get("ego_move") or {}).get("social_move") or "")
    residue = str((conflict_state.get("residue") or {}).get("visible_emotion") or "")
    if not ego_move and not residue:
        return None
    return {
        "event_type": request.get("user_message", "")[:80],
        "ego_move": ego_move,
        "residue": residue,
        "user_impact": "",
        "relationship_delta": (
            (relationship_state.get("durable", {}) or {}).get("relationship_stage", "")
        ),
    }
