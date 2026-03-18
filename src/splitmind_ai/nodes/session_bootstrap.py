"""SessionBootstrapNode: initializes next-generation turn state from input and markdown memory."""

from __future__ import annotations

import logging
import uuid
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.app.logging_utils import preview_text
from splitmind_ai.memory.markdown_store import MarkdownMemoryStore
from splitmind_ai.personas.loader import load_persona

logger = logging.getLogger(__name__)

# Defaults when the persistent store has no prior state
_DEFAULT_RELATIONSHIP_STATE: dict[str, Any] = {
    "durable": {
        "trust": 0.5,
        "intimacy": 0.3,
        "distance": 0.5,
        "attachment_pull": 0.3,
        "relationship_stage": "unfamiliar",
        "commitment_readiness": 0.0,
        "repair_depth": 0.0,
        "unresolved_tension_summary": [],
    },
    "ephemeral": {
        "tension": 0.0,
        "recent_relational_charge": 0.0,
        "escalation_allowed": False,
        "interaction_fragility": 0.0,
        "turn_local_repair_opening": 0.0,
        "repair_mode": "closed",
    },
}

_DEFAULT_MOOD: dict[str, Any] = {
    "base_mood": "calm",
    "irritation": 0.0,
    "longing": 0.0,
    "protectiveness": 0.0,
    "fatigue": 0.0,
    "openness": 0.5,
    "turns_since_shift": 0,
}

class SessionBootstrapNode(ModularNode):
    CONTRACT: ClassVar[NodeContract] = NodeContract(
        name="session_bootstrap",
        description="Normalize session input, load persona and persisted state from markdown memory",
        reads=["request", "_internal"],
        writes=[
            "conversation",
            "persona",
            "relational_policy",
            "relationship_state",
            "mood",
            "memory",
            "working_memory",
            "residue_state",
            "drive_state",
            "_internal",
        ],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=100,
                when={"_internal.is_first_turn": True},
                llm_hint="Run at the start of every session turn",
            ),
        ],
        is_terminal=False,
        icon="🚀",
    )

    def __init__(
        self,
        persona_name: str = "cold_attached_idol",
        memory_store: MarkdownMemoryStore | None = None,
        **services: Any,
    ) -> None:
        super().__init__(**services)
        self._persona_name = persona_name
        self._memory_store = memory_store

    async def execute(self, inputs: NodeInputs, config: Any = None) -> NodeOutputs:
        request = inputs.get_slice("request")
        internal = inputs.get_slice("_internal")

        session_id = request.get("session_id") or str(uuid.uuid4())
        user_id = request.get("user_id", "default")
        user_message = request.get("message") or request.get("user_message", "")
        logger.debug(
            "session_bootstrap start session_id=%s user_id=%s is_first_turn=%s turn_count=%s message=%s",
            session_id,
            user_id,
            internal.get("is_first_turn"),
            internal.get("turn_count"),
            preview_text(user_message),
        )

        # Load persona
        try:
            persona_config = load_persona(self._persona_name)
            persona_slice = persona_config.to_slice()
        except FileNotFoundError:
            logger.warning("Persona '%s' not found, using empty defaults", self._persona_name)
            persona_slice = _default_persona_slice(self._persona_name)

        turn_number = internal.get("turn_count", 0) + 1

        # Load persisted state from markdown memory (session start only)
        relationship_state = {
            "durable": dict(_DEFAULT_RELATIONSHIP_STATE["durable"]),
            "ephemeral": dict(_DEFAULT_RELATIONSHIP_STATE["ephemeral"]),
        }
        mood = dict(_DEFAULT_MOOD)
        memory: dict[str, Any] = {
            "relationship_card": {},
            "psychological_card": {},
            "episodes": [],
            "session_digests": [],
            "session_summaries": [],
            "emotional_memories": [],
            "semantic_preferences": [],
        }

        if self._memory_store is not None:
            try:
                retrieval_params = _extract_memory_retrieval_params(request)
                bootstrap = self._memory_store.load_bootstrap_context(
                    user_id=user_id,
                    persona_name=self._persona_name,
                    query_context={
                        **retrieval_params,
                        "user_message": user_message,
                        "current_episode_summary": str(request.get("message", "") or ""),
                        "unresolved_tension_summary": [],
                    },
                )
                loaded_relationship = dict((bootstrap.get("relationship_state", {}) or {}).get("durable", {}) or {})
                for key, value in loaded_relationship.items():
                    if key in relationship_state["durable"]:
                        relationship_state["durable"][key] = value
                loaded_mood = dict(bootstrap.get("mood", {}) or {})
                for key, value in loaded_mood.items():
                    if key in mood:
                        mood[key] = value
                loaded_memory = dict(bootstrap.get("memory", {}) or {})
                if loaded_memory:
                    memory.update(loaded_memory)
                logger.info(
                    "Loaded memory context: %d sessions, %d episodes, %d guidance items",
                    len(memory.get("session_summaries", [])),
                    len(memory.get("episodes", [])),
                    len(memory.get("semantic_preferences", [])),
                )
            except Exception:
                logger.warning("Failed to load memory from markdown store", exc_info=True)

        # Initialize conversation
        conversation = {
            "recent_messages": [],
            "summary": None,
            "turn_count": turn_number,
        }
        working_memory = {
            "active_themes": _derive_active_themes(memory),
            "salient_user_phrases": [],
            "retrieved_memory_ids": _derive_retrieved_memory_ids(memory),
            "unresolved_questions": [],
            "current_episode_summary": None,
            "recent_conflict_summaries": [],
        }

        # Internal session metadata
        internal_update: dict[str, Any] = {
            "session": {
                "session_id": session_id,
                "persona_name": self._persona_name,
                "persona_self_name": str(((persona_slice.get("identity") or {}).get("self_name")) or ""),
                "user_id": user_id,
            },
            "event_flags": {},
            "errors": [],
            "status": "bootstrapped",
            "is_first_turn": False,
            "turn_count": turn_number,
        }

        return NodeOutputs(
            conversation=conversation,
            persona=persona_slice,
            relational_policy=dict(persona_slice.get("relational_policy", {}) or {}),
            relationship_state=relationship_state,
            mood=mood,
            memory=memory,
            working_memory=working_memory,
            residue_state={"active_residues": [], "dominant_residue": "", "overall_load": 0.0, "trigger_links": []},
            drive_state={},
            _internal=internal_update,
        )


def _default_persona_slice(persona_name: str) -> dict[str, Any]:
    return {
        "persona_version": 2,
        "identity": {
            "self_name": persona_name,
            "display_name": persona_name.replace("_", " "),
        },
        "gender": "other",
        "psychodynamics": {
            "drives": {},
            "threat_sensitivity": {},
            "superego_configuration": {},
        },
        "relational_profile": {
            "attachment_pattern": "unknown",
            "default_role_frame": "default",
            "intimacy_regulation": {},
            "trust_dynamics": {},
            "dependency_model": {},
            "exclusivity_orientation": {},
            "repair_orientation": {},
        },
        "defense_organization": {
            "primary_defenses": {},
            "secondary_defenses": {},
        },
        "ego_organization": {
            "affect_tolerance": 0.5,
            "impulse_regulation": 0.5,
            "ambivalence_capacity": 0.5,
            "mentalization": 0.5,
            "self_observation": 0.5,
            "self_disclosure_tolerance": 0.5,
            "warmth_recovery_speed": 0.5,
        },
        "safety_boundary": {
            "hard_limits": {},
        },
        "relational_policy": {
            "repair_style": "guarded",
            "comparison_style": "withhold",
            "distance_management_style": "respect_space",
            "status_maintenance_style": "medium",
            "warmth_release_style": "measured",
            "priority_response_style": "implicit",
            "residue_persistence": {},
        },
    }


def _extract_memory_retrieval_params(request: dict[str, Any]) -> dict[str, Any]:
    params = request.get("params") or {}
    return {
        "query": params.get("memory_query"),
        "trigger": params.get("memory_trigger"),
        "wound": params.get("memory_wound"),
        "target": params.get("memory_target"),
        "blocked_action": params.get("memory_blocked_action"),
        "topic": params.get("memory_topic"),
        "active_themes": params.get("active_themes", []),
        "limit": params.get("memory_limit", 3),
    }


def _derive_active_themes(memory: dict[str, Any]) -> list[str]:
    themes: list[str] = []
    for item in memory.get("episodes", []):
        for value in item.get("themes", []) or []:
            if value and value not in themes:
                themes.append(value)
    psychological_card = dict(memory.get("psychological_card", {}) or {})
    for value in psychological_card.get("active_themes", []) or []:
        if value and value not in themes:
            themes.append(value)
    for item in memory.get("emotional_memories", []):
        trigger = item.get("trigger")
        target = item.get("target")
        emotion = item.get("emotion")
        wound = item.get("wound")
        residual_drive = item.get("residual_drive")
        blocked_action = item.get("blocked_action")
        for value in (trigger, target, emotion, wound, residual_drive, blocked_action):
            if value and value not in themes:
                themes.append(value)
    return themes[:5]


def _derive_retrieved_memory_ids(memory: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in memory.get("episodes", []):
        item_id = item.get("id")
        session_id = item.get("session_id")
        if item_id:
            ids.append(str(item_id))
        elif session_id:
            ids.append(str(session_id))
    for item in memory.get("emotional_memories", []):
        session_id = item.get("session_id")
        turn_number = item.get("turn_number")
        event = item.get("event")
        if session_id:
            ids.append(f"{session_id}:{turn_number or 0}")
        elif event:
            ids.append(event[:40])
    return ids[:5]
