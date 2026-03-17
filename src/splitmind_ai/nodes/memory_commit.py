"""MemoryCommitNode: rule-based state update + vault persistence.

Delegates state update logic to rules.state_updates engine.
Writes updated state to Obsidian vault via VaultStore.

Reads: request, response, relationship, mood, memory, working_memory, dynamics, drive_state, inhibition_state, conversation_policy, _internal
Writes: relationship, mood, memory, working_memory, trace, _internal
Trigger: response.final_response_text exists
"""

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
        description="Rule-based state update and vault persistence (no LLM)",
        reads=[
            "request",
            "response",
            "relationship",
            "mood",
            "memory",
            "working_memory",
            "dynamics",
            "drive_state",
            "inhibition_state",
            "conversation_policy",
            "_internal",
        ],
        writes=["relationship", "mood", "memory", "working_memory", "trace", "_internal"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=40,
                when={"response.final_response_text": True},
                llm_hint="Run after the final response has been generated",
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
        relationship = dict(inputs.get_slice("relationship"))
        mood = dict(inputs.get_slice("mood"))
        memory = dict(inputs.get_slice("memory"))
        working_memory = dict(inputs.get_slice("working_memory"))
        dynamics = inputs.get_slice("dynamics")
        drive_state = inputs.get_slice("drive_state")
        inhibition_state = inputs.get_slice("inhibition_state")
        conversation_policy = inputs.get_slice("conversation_policy")
        internal = inputs.get_slice("_internal")
        request = inputs.get_slice("request")
        response = inputs.get_slice("response")

        event_flags: dict[str, bool] = internal.get("event_flags", {})
        logger.debug(
            "memory_commit start user_id=%s dominant_desire=%s active_flags=%s response=%s",
            internal.get("session", {}).get("user_id", request.get("user_id", "default")),
            dynamics.get("dominant_desire"),
            [k for k, v in event_flags.items() if v],
            preview_text(response.get("final_response_text")),
        )

        # Delegate to centralized state update engine
        session_info = internal.get("session", {})
        result = run_full_update(
            relationship=relationship,
            mood=mood,
            event_flags=event_flags,
            dynamics=dynamics,
            request=request,
            response=response,
            rules=self._rules,
            session_id=session_info.get("session_id", ""),
            turn_number=internal.get("turn_count", 0),
        )

        updated_rel = result["relationship"]
        updated_mood = result["mood"]
        memory_candidates = _enrich_memory_candidates(
            memory_candidates=result["memory_candidates"],
            drive_state=drive_state,
            inhibition_state=inhibition_state,
            conversation_policy=conversation_policy,
        )
        updated_memory = _merge_memory_context(memory, memory_candidates)
        updated_working_memory = _merge_working_memory(
            working_memory=working_memory,
            relationship=updated_rel,
            request=request,
            dynamics=dynamics,
            drive_state=drive_state,
            memory_candidates=memory_candidates,
            event_flags=event_flags,
        )

        # Persist to vault
        user_id = internal.get("session", {}).get("user_id", request.get("user_id", "default"))
        vault_committed = False

        if self._vault is not None:
            try:
                self._vault.commit_turn(
                    user_id=user_id,
                    relationship=updated_rel,
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
            updated_rel.get("trust", 0.0),
            updated_rel.get("tension", 0.0),
            updated_mood.get("base_mood"),
            vault_committed,
        )

        return NodeOutputs(
            relationship=updated_rel,
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
    relationship: dict[str, Any],
    request: dict[str, Any],
    dynamics: dict[str, Any],
    drive_state: dict[str, Any],
    memory_candidates: dict[str, list[dict[str, Any]]],
    event_flags: dict[str, bool],
) -> dict[str, Any]:
    updated = {
        "active_themes": list(working_memory.get("active_themes", [])),
        "salient_user_phrases": list(working_memory.get("salient_user_phrases", [])),
        "retrieved_memory_ids": list(working_memory.get("retrieved_memory_ids", [])),
        "unresolved_questions": list(working_memory.get("unresolved_questions", [])),
        "current_episode_summary": working_memory.get("current_episode_summary"),
        "last_user_intent_prediction": working_memory.get("last_user_intent_prediction"),
    }

    user_message = request.get("user_message", "")
    if user_message:
        updated["salient_user_phrases"] = [user_message[:120], *updated["salient_user_phrases"]][:5]

    updated["active_themes"] = _rank_active_themes(
        existing_themes=updated["active_themes"],
        relationship=relationship,
        dynamics=dynamics,
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

    if user_message:
        updated["current_episode_summary"] = user_message[:160]

    return updated


def _rank_active_themes(
    *,
    existing_themes: list[str],
    relationship: dict[str, Any],
    dynamics: dict[str, Any],
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
    unresolved = relationship.get("unresolved_tensions", []) or []
    unresolved_theme_names = {
        item.get("theme")
        for item in unresolved
        if isinstance(item, dict) and item.get("theme")
    }
    base_order = len(first_seen)

    for offset, tension in enumerate(unresolved):
        if not isinstance(tension, dict):
            continue
        theme = tension.get("theme")
        intensity = float(tension.get("intensity", 0.0) or 0.0)
        if resolution_turn:
            add(theme, 0.2 + (intensity * 0.35), base_order + offset)
        else:
            add(theme, 0.25 + (intensity * 0.55), base_order + offset)

    dominant_desire = dynamics.get("dominant_desire")
    affective_pressure = float(dynamics.get("affective_pressure", 0.0) or 0.0)
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
    inhibition_state: dict[str, Any],
    conversation_policy: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    updated = {
        "emotional_memories": [dict(item) for item in memory_candidates.get("emotional_memories", [])],
        "semantic_preferences": [dict(item) for item in memory_candidates.get("semantic_preferences", [])],
    }
    top_drives = list(drive_state.get("top_drives", []) or [])
    primary_drive = top_drives[0] if top_drives else {}
    target = primary_drive.get("target") or (drive_state.get("drive_targets", {}) or {}).get(primary_drive.get("name"))
    blocked_modes = list(inhibition_state.get("blocked_modes", []) or [])
    attempted_action = conversation_policy.get("selected_mode") or ""
    residual_drive = primary_drive.get("name") or ""

    for memory in updated["emotional_memories"]:
        memory.setdefault("target", target)
        memory.setdefault("blocked_action", blocked_modes[0] if blocked_modes else "")
        memory.setdefault("attempted_action", attempted_action)
        memory.setdefault("residual_drive", residual_drive or memory.get("trigger", ""))

    return updated
