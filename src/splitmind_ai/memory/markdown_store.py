"""Frontmatter-backed markdown store for persistent SplitMind memory."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter

logger = logging.getLogger(__name__)


class MarkdownMemoryStore:
    """Persist long-term memory as frontmatter-backed markdown cards."""

    MAX_EPISODES = 60
    BOOTSTRAP_EPISODE_LIMIT = 4
    SESSION_DIGEST_LIMIT = 3

    def __init__(self, root_path: str | Path) -> None:
        self._root = Path(root_path).resolve()

    def load_bootstrap_context(
        self,
        user_id: str,
        persona_name: str,
        query_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load the minimum cross-session context needed at session start."""
        relationship_card = self._load_relationship_card(user_id, persona_name)
        psychological_card = self._load_psychological_card(user_id, persona_name)
        session_digests = self._load_recent_session_digests(user_id, persona_name)
        episodes = self._retrieve_relevant_episodes(user_id, persona_name, query_context or {})

        durable = dict((relationship_card or {}).get("durable", {}) or {})
        mood = dict((psychological_card or {}).get("mood", {}) or {})

        memory = {
            "relationship_card": relationship_card or {},
            "psychological_card": psychological_card or {},
            "episodes": episodes,
            "session_digests": session_digests,
            # Compatibility aliases for the current runtime/UI.
            "session_summaries": session_digests,
            "emotional_memories": episodes,
            "semantic_preferences": [
                {
                    "topic": "effective_approach",
                    "preference": str(item),
                    "confidence": 0.7,
                }
                for item in list((psychological_card or {}).get("effective_approaches", []) or [])
            ],
        }

        return {
            "relationship_state": {"durable": durable} if durable else {},
            "mood": mood,
            "memory": memory,
        }

    def commit_turn(
        self,
        user_id: str,
        persona_name: str,
        relationship_state: dict[str, Any],
        mood: dict[str, Any],
        memory_interpretation: dict[str, Any],
        working_memory: dict[str, Any],
    ) -> None:
        """Persist turn-level durable cards and salient episodic memory."""
        self._ensure_scope_dirs(user_id, persona_name)
        self._save_relationship_card(user_id, persona_name, relationship_state)
        self._save_psychological_card(
            user_id=user_id,
            persona_name=persona_name,
            relationship_state=relationship_state,
            mood=mood,
            memory_interpretation=memory_interpretation,
            working_memory=working_memory,
        )

        episode = self._build_episode(memory_interpretation, working_memory)
        if episode is not None:
            self._save_episode(user_id, persona_name, episode)
            self._compact_episodes(user_id, persona_name)

    def commit_session(
        self,
        user_id: str,
        persona_name: str,
        session_id: str,
        session_digest: dict[str, Any],
        final_state: dict[str, Any],
    ) -> None:
        """Persist a session digest at session end."""
        self._ensure_scope_dirs(user_id, persona_name)
        path = self._sessions_dir(user_id, persona_name) / f"{session_id}.md"
        now = _iso_now()
        metadata = {
            "type": "session_digest",
            "user_id": user_id,
            "persona_name": persona_name,
            "session_id": session_id,
            "turn_count": int(session_digest.get("turn_count", 0) or 0),
            "dominant_mood": str(
                session_digest.get("dominant_mood")
                or ((final_state.get("mood", {}) or {}).get("base_mood", "calm"))
            ),
            "key_events": list(session_digest.get("key_events", []) or []),
            "relationship_stage": str(
                (((final_state.get("relationship_state", {}) or {}).get("durable", {}) or {}).get(
                    "relationship_stage",
                    "",
                ))
            ),
            "created_at": now,
        }
        post = frontmatter.Post(str(session_digest.get("text", "") or ""), **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _scope_dir(self, user_id: str, persona_name: str) -> Path:
        return self._root / user_id / persona_name

    def _episodes_dir(self, user_id: str, persona_name: str) -> Path:
        return self._scope_dir(user_id, persona_name) / "episodes"

    def _sessions_dir(self, user_id: str, persona_name: str) -> Path:
        return self._scope_dir(user_id, persona_name) / "sessions"

    def _ensure_scope_dirs(self, user_id: str, persona_name: str) -> None:
        scope = self._scope_dir(user_id, persona_name)
        scope.mkdir(parents=True, exist_ok=True)
        self._episodes_dir(user_id, persona_name).mkdir(parents=True, exist_ok=True)
        self._sessions_dir(user_id, persona_name).mkdir(parents=True, exist_ok=True)

    def _load_relationship_card(self, user_id: str, persona_name: str) -> dict[str, Any] | None:
        path = self._scope_dir(user_id, persona_name) / "relationship-card.md"
        if not path.exists():
            return None
        try:
            post = frontmatter.load(str(path))
            durable = dict(post.metadata.get("durable", {}) or {})
            return {
                "durable": durable,
                "summary": post.content.strip(),
                "updated_at": post.metadata.get("updated_at", ""),
            }
        except Exception:
            logger.warning("Failed to load relationship card from %s", path, exc_info=True)
            return None

    def _load_psychological_card(self, user_id: str, persona_name: str) -> dict[str, Any] | None:
        path = self._scope_dir(user_id, persona_name) / "psychological-card.md"
        if not path.exists():
            return None
        try:
            post = frontmatter.load(str(path))
            return {
                **dict(post.metadata),
                "summary": post.content.strip(),
            }
        except Exception:
            logger.warning("Failed to load psychological card from %s", path, exc_info=True)
            return None

    def _load_recent_session_digests(self, user_id: str, persona_name: str) -> list[dict[str, Any]]:
        files = sorted(
            self._sessions_dir(user_id, persona_name).glob("*.md"),
            reverse=True,
        )[: self.SESSION_DIGEST_LIMIT]
        digests: list[dict[str, Any]] = []
        for file in files:
            try:
                post = frontmatter.load(str(file))
                digests.append({**dict(post.metadata), "summary": post.content.strip()})
            except Exception:
                logger.warning("Failed to load session digest %s", file, exc_info=True)
        return digests

    def _retrieve_relevant_episodes(
        self,
        user_id: str,
        persona_name: str,
        query_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for file in self._episodes_dir(user_id, persona_name).glob("*.md"):
            try:
                post = frontmatter.load(str(file))
            except Exception:
                logger.warning("Failed to load episode %s", file, exc_info=True)
                continue
            entry = {
                **dict(post.metadata),
                "summary": post.content.strip(),
                "id": file.stem,
            }
            score = self._episode_score(entry, query_context)
            scored.append((score, entry))

        scored.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("created_at", "")),
            ),
        )
        return [entry for _score, entry in scored[: self.BOOTSTRAP_EPISODE_LIMIT]]

    def _episode_score(self, entry: dict[str, Any], query_context: dict[str, Any]) -> float:
        salience = float(entry.get("salience", 0.0) or 0.0)
        haystack = " ".join(
            [
                str(entry.get("summary", "")),
                " ".join(str(theme) for theme in (entry.get("themes", []) or [])),
                str(entry.get("relationship_delta", "")),
                str(entry.get("user_impact", "")),
            ]
        ).lower()

        query_terms: list[str] = []
        user_message = str(query_context.get("user_message", "") or "")
        if user_message:
            query_terms.extend(_normalize_terms(user_message))
        for key, value in query_context.items():
            if key == "user_message":
                continue
            if isinstance(value, str):
                query_terms.extend(_normalize_terms(value))
            elif isinstance(value, list):
                for item in value:
                    query_terms.extend(_normalize_terms(str(item)))

        overlap = 0.0
        for term in query_terms:
            if term and term in haystack:
                overlap += 0.18
        return salience + overlap

    def _save_relationship_card(
        self,
        user_id: str,
        persona_name: str,
        relationship_state: dict[str, Any],
    ) -> None:
        path = self._scope_dir(user_id, persona_name) / "relationship-card.md"
        durable = dict((relationship_state.get("durable", {}) or {}))
        metadata = {
            "type": "relationship_card",
            "user_id": user_id,
            "persona_name": persona_name,
            "durable": durable,
            "updated_at": _iso_now(),
        }
        summary = _render_relationship_card_summary(durable)
        post = frontmatter.Post(summary, **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _save_psychological_card(
        self,
        *,
        user_id: str,
        persona_name: str,
        relationship_state: dict[str, Any],
        mood: dict[str, Any],
        memory_interpretation: dict[str, Any],
        working_memory: dict[str, Any],
    ) -> None:
        path = self._scope_dir(user_id, persona_name) / "psychological-card.md"
        previous = self._load_psychological_card(user_id, persona_name) or {}
        event_flags = {
            str(key): bool(value)
            for key, value in (memory_interpretation.get("event_flags", {}) or {}).items()
        }
        active_themes = _unique_preserve_order(
            [
                *list(memory_interpretation.get("active_themes", []) or []),
                *list(working_memory.get("active_themes", []) or []),
            ]
        )[:6]
        sensitivities = _unique_preserve_order(
            [
                *list(memory_interpretation.get("unresolved_tension_summary", []) or []),
                *list(previous.get("sensitivities", []) or []),
            ]
        )[:6]
        effective_approaches = _unique_preserve_order(
            [
                *list(previous.get("effective_approaches", []) or []),
                *_event_flags_to_guidance(event_flags, positive=True),
            ]
        )[:6]
        avoid_patterns = _unique_preserve_order(
            [
                *list(previous.get("avoid_patterns", []) or []),
                *_event_flags_to_guidance(event_flags, positive=False),
            ]
        )[:6]
        relationship_stage = str(
            (((relationship_state.get("durable", {}) or {}).get("relationship_stage")) or "unfamiliar")
        )
        metadata = {
            "type": "psychological_card",
            "user_id": user_id,
            "persona_name": persona_name,
            "current_relational_stance": relationship_stage,
            "active_themes": active_themes,
            "sensitivities": sensitivities,
            "effective_approaches": effective_approaches,
            "avoid_patterns": avoid_patterns,
            "mood": {k: v for k, v in mood.items() if isinstance(v, (int, float, str, bool))},
            "updated_at": _iso_now(),
        }
        summary_lines = [
            f"Current stance: {relationship_stage}",
            f"Base mood: {mood.get('base_mood', 'calm')}",
        ]
        if active_themes:
            summary_lines.append(f"Active themes: {', '.join(active_themes)}")
        if sensitivities:
            summary_lines.append(f"Sensitivities: {', '.join(sensitivities)}")
        if effective_approaches:
            summary_lines.append(f"Effective approaches: {', '.join(effective_approaches)}")
        if avoid_patterns:
            summary_lines.append(f"Avoid patterns: {', '.join(avoid_patterns)}")

        post = frontmatter.Post("\n".join(summary_lines), **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _build_episode(
        self,
        memory_interpretation: dict[str, Any],
        working_memory: dict[str, Any],
    ) -> dict[str, Any] | None:
        summary = str(memory_interpretation.get("current_episode_summary", "") or "").strip()
        conflict_summary = memory_interpretation.get("recent_conflict_summary") or {}
        if not summary and isinstance(conflict_summary, dict):
            parts = [
                str(conflict_summary.get("event_type", "") or ""),
                str(conflict_summary.get("ego_move", "") or ""),
                str(conflict_summary.get("residue", "") or ""),
            ]
            summary = " / ".join(part for part in parts if part)

        if not summary:
            return None

        emotional = list(memory_interpretation.get("emotional_memories", []) or [])
        primary = emotional[0] if emotional and isinstance(emotional[0], dict) else {}
        salience = max(
            float(primary.get("intensity", 0.0) or 0.0),
            0.35 if memory_interpretation.get("unresolved_tension_summary") else 0.0,
            0.4 if memory_interpretation.get("event_flags") else 0.0,
        )
        return {
            "summary": summary[:280],
            "themes": _unique_preserve_order(
                [
                    *list(memory_interpretation.get("active_themes", []) or []),
                    *list(working_memory.get("active_themes", []) or []),
                ]
            )[:6],
            "salience": round(min(1.0, max(0.2, salience)), 2),
            "session_id": str(primary.get("session_id", "") or ""),
            "turn_number": int(primary.get("turn_number", 0) or 0),
            "relationship_delta": str((conflict_summary or {}).get("relationship_delta", "") or ""),
            "user_impact": str((conflict_summary or {}).get("user_impact", "") or ""),
            "created_at": str(primary.get("created_at", "") or _iso_now()),
        }

    def _save_episode(self, user_id: str, persona_name: str, episode: dict[str, Any]) -> None:
        timestamp = _compact_timestamp(episode.get("created_at"))
        slug = _sanitize_filename(str(episode.get("summary", "episode"))[:48])
        path = self._episodes_dir(user_id, persona_name) / f"{timestamp}-{slug}.md"
        suffix = 1
        while path.exists():
            path = self._episodes_dir(user_id, persona_name) / f"{timestamp}-{slug}-{suffix}.md"
            suffix += 1
        metadata = {
            "type": "episode",
            "user_id": user_id,
            "persona_name": persona_name,
            "themes": list(episode.get("themes", []) or []),
            "salience": float(episode.get("salience", 0.0) or 0.0),
            "session_id": str(episode.get("session_id", "") or ""),
            "turn_number": int(episode.get("turn_number", 0) or 0),
            "relationship_delta": str(episode.get("relationship_delta", "") or ""),
            "user_impact": str(episode.get("user_impact", "") or ""),
            "created_at": str(episode.get("created_at", "") or _iso_now()),
            "last_used_at": "",
        }
        post = frontmatter.Post(str(episode.get("summary", "") or ""), **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def _compact_episodes(self, user_id: str, persona_name: str) -> None:
        files = sorted(self._episodes_dir(user_id, persona_name).glob("*.md"), reverse=True)
        if len(files) <= self.MAX_EPISODES:
            return

        compact_targets = list(reversed(files[self.MAX_EPISODES - 1 :]))
        items: list[dict[str, Any]] = []
        for file in compact_targets:
            try:
                post = frontmatter.load(str(file))
                items.append({**dict(post.metadata), "summary": post.content.strip()})
            except Exception:
                logger.warning("Failed to load episode for compaction: %s", file, exc_info=True)
        if not items:
            return

        merged_summary = "\n".join(
            f"- {item.get('summary', '')}"
            for item in items[:8]
            if item.get("summary")
        )[:1200]
        merged_episode = {
            "summary": merged_summary or "Compacted historical episodes",
            "themes": _unique_preserve_order(
                [theme for item in items for theme in (item.get("themes", []) or [])]
            )[:8],
            "salience": round(
                min(
                    1.0,
                    max(float(item.get("salience", 0.0) or 0.0) for item in items) * 0.85,
                ),
                2,
            ),
            "session_id": "",
            "turn_number": 0,
            "relationship_delta": "compacted_history",
            "user_impact": "",
            "created_at": _iso_now(),
        }
        self._save_episode(user_id, persona_name, merged_episode)
        for file in compact_targets:
            try:
                file.unlink(missing_ok=True)
            except Exception:
                logger.warning("Failed to delete compacted episode %s", file, exc_info=True)


def _render_relationship_card_summary(durable: dict[str, Any]) -> str:
    unresolved = list(durable.get("unresolved_tension_summary", []) or [])
    lines = [
        f"Trust: {float(durable.get('trust', 0.0) or 0.0):.2f}",
        f"Intimacy: {float(durable.get('intimacy', 0.0) or 0.0):.2f}",
        f"Distance: {float(durable.get('distance', 0.0) or 0.0):.2f}",
        f"Attachment pull: {float(durable.get('attachment_pull', 0.0) or 0.0):.2f}",
        f"Relationship stage: {durable.get('relationship_stage', 'unfamiliar')}",
    ]
    if unresolved:
        lines.append(f"Unresolved themes: {', '.join(str(item) for item in unresolved)}")
    return "\n".join(lines)


def _event_flags_to_guidance(event_flags: dict[str, bool], *, positive: bool) -> list[str]:
    positive_map = {
        "reassurance_received": "steady reassurance helps",
        "affectionate_exchange": "warm reciprocal tone helps",
        "repair_attempt": "clear repair language helps",
    }
    negative_map = {
        "rejection_signal": "avoid abrupt rejection framing",
        "jealousy_trigger": "avoid third-party comparison pressure",
        "user_praised_third_party": "avoid status comparison pressure",
        "prolonged_avoidance": "avoid emotional disappearance",
    }
    mapping = positive_map if positive else negative_map
    return [label for key, label in mapping.items() if event_flags.get(key)]


def _normalize_terms(text: str) -> list[str]:
    separators = ",.;:!?/()[]{}<>\n\t"
    normalized = text.lower()
    for separator in separators:
        normalized = normalized.replace(separator, " ")
    return [token for token in normalized.split(" ") if len(token) >= 3][:12]


def _unique_preserve_order(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _compact_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return dt.astimezone(UTC).strftime("%Y%m%d_%H%M%S")


def _sanitize_filename(value: str) -> str:
    sanitized = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
    return sanitized[:48] or "memory"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()
