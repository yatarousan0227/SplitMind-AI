"""Obsidian Vault memory store.

Handles reading and writing long-term memory artifacts to the Obsidian vault
using Markdown files with YAML frontmatter.

Vault layout:
    vault/
    ├── users/
    │   └── <user_id>/
    │       ├── relationship.md
    │       ├── sessions/
    │       │   └── <session_id>.md
    │       ├── emotional_memories/
    │       │   └── <timestamp>-<theme>.md
    │       └── preferences/
    │           └── <topic>.md
    └── system/
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter

logger = logging.getLogger(__name__)


class VaultStore:
    """Read/write interface to the Obsidian vault."""

    def __init__(self, vault_path: str | Path) -> None:
        self._root = Path(vault_path).resolve()

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    def _user_dir(self, user_id: str) -> Path:
        return self._root / "users" / user_id

    def _ensure_dirs(self, user_id: str) -> None:
        base = self._user_dir(user_id)
        for sub in ("sessions", "emotional_memories", "preferences"):
            (base / sub).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Relationship snapshot
    # ------------------------------------------------------------------

    def load_relationship(self, user_id: str) -> dict[str, Any] | None:
        """Load the latest relationship snapshot from vault."""
        path = self._user_dir(user_id) / "relationship.md"
        if not path.exists():
            return None
        try:
            post = frontmatter.load(str(path))
            data = dict(post.metadata)
            # unresolved_tensions may be stored as content body
            if post.content.strip():
                import json
                try:
                    data["unresolved_tensions"] = json.loads(post.content)
                except json.JSONDecodeError:
                    pass
            return data
        except Exception:
            logger.warning("Failed to load relationship from %s", path, exc_info=True)
            return None

    def save_relationship(self, user_id: str, relationship: dict[str, Any]) -> None:
        """Save relationship snapshot to vault (overwrite)."""
        self._ensure_dirs(user_id)
        path = self._user_dir(user_id) / "relationship.md"

        import json

        rel = dict(relationship)
        unresolved = rel.pop("unresolved_tensions", [])

        metadata = {
            "type": "relationship_snapshot",
            "user_id": user_id,
            "updated_at": datetime.now().isoformat(),
            **{k: v for k, v in rel.items() if isinstance(v, (int, float, str, bool))},
        }

        content = json.dumps(unresolved, ensure_ascii=False, indent=2) if unresolved else ""

        post = frontmatter.Post(content, **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ------------------------------------------------------------------
    # Session summaries
    # ------------------------------------------------------------------

    def load_recent_sessions(self, user_id: str, limit: int = 3) -> list[dict[str, Any]]:
        """Load recent session summaries, newest first."""
        sessions_dir = self._user_dir(user_id) / "sessions"
        if not sessions_dir.exists():
            return []

        files = sorted(sessions_dir.glob("*.md"), reverse=True)[:limit]
        results = []
        for f in files:
            try:
                post = frontmatter.load(str(f))
                entry = dict(post.metadata)
                entry["summary"] = post.content.strip()
                results.append(entry)
            except Exception:
                logger.warning("Failed to load session %s", f, exc_info=True)
        return results

    def save_session_summary(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        turn_count: int,
        dominant_mood: str,
        key_events: list[str] | None = None,
    ) -> None:
        """Save a session summary."""
        self._ensure_dirs(user_id)
        path = self._user_dir(user_id) / "sessions" / f"{session_id}.md"

        metadata = {
            "type": "session_summary",
            "user_id": user_id,
            "session_id": session_id,
            "turn_count": turn_count,
            "dominant_mood": dominant_mood,
            "key_events": key_events or [],
            "created_at": datetime.now().isoformat(),
        }

        post = frontmatter.Post(summary, **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ------------------------------------------------------------------
    # Emotional memories
    # ------------------------------------------------------------------

    def load_emotional_memories(
        self,
        user_id: str,
        limit: int = 3,
        theme_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load emotional memories, newest first."""
        mem_dir = self._user_dir(user_id) / "emotional_memories"
        if not mem_dir.exists():
            return []

        files = sorted(mem_dir.glob("*.md"), reverse=True)
        results = []
        for f in files:
            if len(results) >= limit:
                break
            try:
                post = frontmatter.load(str(f))
                entry = dict(post.metadata)
                entry["details"] = post.content.strip()
                entry["event"] = entry.get("event") or _extract_first_nonempty_line(post.content)
                if (
                    theme_filter
                    and entry.get("emotion") != theme_filter
                    and entry.get("trigger") != theme_filter
                    and entry.get("residual_drive") != theme_filter
                ):
                    continue
                results.append(entry)
            except Exception:
                logger.warning("Failed to load emotional memory %s", f, exc_info=True)
        return results

    def save_emotional_memory(self, user_id: str, memory: dict[str, Any]) -> None:
        """Append an emotional memory."""
        self._ensure_dirs(user_id)
        mem_dir = self._user_dir(user_id) / "emotional_memories"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        emotion = _sanitize_filename(memory.get("emotion", "unknown"))
        path = mem_dir / f"{ts}-{emotion}.md"

        metadata = {
            "type": "emotional_memory",
            "user_id": user_id,
            "event": memory.get("event", ""),
            "emotion": memory.get("emotion", ""),
            "trigger": memory.get("trigger", ""),
            "target": memory.get("target", ""),
            "wound": memory.get("wound", ""),
            "blocked_action": memory.get("blocked_action", ""),
            "attempted_action": memory.get("attempted_action", ""),
            "action_tendency": memory.get("action_tendency", ""),
            "interaction_outcome": memory.get("interaction_outcome", ""),
            "residual_drive": memory.get("residual_drive", ""),
            "intensity": memory.get("intensity", 0.0),
            "session_id": memory.get("session_id", ""),
            "turn_number": memory.get("turn_number", 0),
            "created_at": memory.get("created_at", datetime.now().isoformat()),
        }

        content_lines = [memory.get("event", "").strip()]
        if memory.get("agent_response"):
            content_lines.extend(["", f"Agent response: {memory['agent_response']}"])
        if memory.get("context"):
            content_lines.extend(["", f"Context: {memory['context']}"])

        episode_fields = [
            ("Trigger", memory.get("trigger")),
            ("Target", memory.get("target")),
            ("Wound", memory.get("wound")),
            ("Blocked action", memory.get("blocked_action")),
            ("Attempted action", memory.get("attempted_action")),
            ("Action tendency", memory.get("action_tendency")),
            ("Outcome", memory.get("interaction_outcome")),
            ("Residual drive", memory.get("residual_drive")),
        ]
        episode_lines = [f"{label}: {value}" for label, value in episode_fields if value]
        if episode_lines:
            content_lines.extend(["", "---", *episode_lines])

        content = "\n".join(line for line in content_lines if line is not None)

        post = frontmatter.Post(content, **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ------------------------------------------------------------------
    # Semantic preferences
    # ------------------------------------------------------------------

    def load_semantic_preferences(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Load semantic preferences."""
        pref_dir = self._user_dir(user_id) / "preferences"
        if not pref_dir.exists():
            return []

        files = sorted(pref_dir.glob("*.md"), reverse=True)[:limit]
        results = []
        for f in files:
            try:
                post = frontmatter.load(str(f))
                entry = dict(post.metadata)
                entry["preference"] = post.content.strip()
                results.append(entry)
            except Exception:
                logger.warning("Failed to load preference %s", f, exc_info=True)
        return results

    def save_semantic_preference(self, user_id: str, preference: dict[str, Any]) -> None:
        """Save or update a semantic preference."""
        self._ensure_dirs(user_id)
        pref_dir = self._user_dir(user_id) / "preferences"

        topic = _sanitize_filename(preference.get("topic", "unknown"))
        path = pref_dir / f"{topic}.md"

        metadata = {
            "type": "semantic_preference",
            "user_id": user_id,
            "topic": preference.get("topic", ""),
            "confidence": preference.get("confidence", 0.5),
            "evidence": preference.get("evidence", ""),
            "episode_hint": preference.get("episode_hint", ""),
            "created_at": preference.get("created_at", datetime.now().isoformat()),
        }

        post = frontmatter.Post(preference.get("preference", ""), **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ------------------------------------------------------------------
    # Mood snapshot
    # ------------------------------------------------------------------

    def load_mood(self, user_id: str) -> dict[str, Any] | None:
        """Load the latest mood snapshot from vault."""
        path = self._user_dir(user_id) / "mood.md"
        if not path.exists():
            return None
        try:
            post = frontmatter.load(str(path))
            return dict(post.metadata)
        except Exception:
            logger.warning("Failed to load mood from %s", path, exc_info=True)
            return None

    def save_mood(self, user_id: str, mood: dict[str, Any]) -> None:
        """Save mood snapshot to vault (overwrite)."""
        self._ensure_dirs(user_id)
        path = self._user_dir(user_id) / "mood.md"

        metadata = {
            "type": "mood_snapshot",
            "user_id": user_id,
            "updated_at": datetime.now().isoformat(),
            **{k: v for k, v in mood.items() if isinstance(v, (int, float, str, bool))},
        }

        post = frontmatter.Post("", **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ------------------------------------------------------------------
    # Bulk load for session bootstrap
    # ------------------------------------------------------------------

    def load_memory_context(self, user_id: str) -> dict[str, Any]:
        """Load full memory context for session bootstrap.

        Returns a dict matching MemorySlice shape:
            session_summaries, emotional_memories, semantic_preferences
        """
        return {
            "session_summaries": self.load_recent_sessions(user_id, limit=3),
            "emotional_memories": self.load_emotional_memories(user_id, limit=3),
            "semantic_preferences": self.load_semantic_preferences(user_id, limit=5),
        }

    def retrieve_relevant_memories(
        self,
        user_id: str,
        *,
        query: str | None = None,
        trigger: str | None = None,
        wound: str | None = None,
        target: str | None = None,
        blocked_action: str | None = None,
        topic: str | None = None,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Targeted retrieval API for future active recall.

        Inputs are soft filters. The current implementation is deterministic
        and string-based so the runtime can adopt the API before vector search.
        """
        emotional = self.load_emotional_memories(user_id, limit=50)
        semantic = self.load_semantic_preferences(user_id, limit=20)

        emotional_filtered = [
            memory
            for memory in emotional
            if _matches_memory_query(
                memory,
                query=query,
                trigger=trigger,
                wound=wound,
                target=target,
                blocked_action=blocked_action,
            )
        ][:limit]
        semantic_filtered = [
            pref
            for pref in semantic
            if _matches_preference_query(pref, query=query, topic=topic)
        ][:limit]

        return {
            "session_summaries": [],
            "emotional_memories": emotional_filtered,
            "semantic_preferences": semantic_filtered,
        }

    # ------------------------------------------------------------------
    # Commit after turn
    # ------------------------------------------------------------------

    def commit_turn(
        self,
        user_id: str,
        relationship: dict[str, Any],
        memory_candidates: dict[str, list[dict[str, Any]]],
        mood: dict[str, Any] | None = None,
    ) -> None:
        """Persist relationship snapshot, mood, and new memory candidates."""
        try:
            self.save_relationship(user_id, relationship)
        except Exception:
            logger.warning("Failed to save relationship snapshot", exc_info=True)

        if mood is not None:
            try:
                self.save_mood(user_id, mood)
            except Exception:
                logger.warning("Failed to save mood snapshot", exc_info=True)

        for em in memory_candidates.get("emotional_memories", []):
            try:
                self.save_emotional_memory(user_id, em)
            except Exception:
                logger.warning("Failed to save emotional memory", exc_info=True)

        for sp in memory_candidates.get("semantic_preferences", []):
            try:
                self.save_semantic_preference(user_id, sp)
            except Exception:
                logger.warning("Failed to save semantic preference", exc_info=True)


def _sanitize_filename(s: str) -> str:
    """Remove characters not safe for filenames."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)[:50]


def _extract_first_nonempty_line(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _matches_memory_query(
    memory: dict[str, Any],
    *,
    query: str | None,
    trigger: str | None,
    wound: str | None,
    target: str | None,
    blocked_action: str | None,
) -> bool:
    haystack = " ".join(
        str(memory.get(key, ""))
        for key in (
            "event",
            "details",
            "emotion",
            "trigger",
            "target",
            "wound",
            "blocked_action",
            "attempted_action",
            "interaction_outcome",
            "residual_drive",
        )
    ).lower()
    if query and query.lower() not in haystack:
        return False
    if trigger and trigger.lower() != str(memory.get("trigger", "")).lower():
        return False
    if wound and wound.lower() != str(memory.get("wound", "")).lower():
        return False
    if target and target.lower() != str(memory.get("target", "")).lower():
        return False
    if blocked_action and blocked_action.lower() != str(memory.get("blocked_action", "")).lower():
        return False
    return True


def _matches_preference_query(
    preference: dict[str, Any],
    *,
    query: str | None,
    topic: str | None,
) -> bool:
    haystack = " ".join(
        str(preference.get(key, ""))
        for key in ("topic", "preference", "evidence", "episode_hint")
    ).lower()
    if query and query.lower() not in haystack:
        return False
    if topic and topic.lower() != str(preference.get("topic", "")).lower():
        return False
    return True
