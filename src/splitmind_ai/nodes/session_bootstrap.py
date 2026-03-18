"""SessionBootstrapNode: initializes next-generation turn state from input and vault."""

from __future__ import annotations

import logging
import uuid
from typing import Any, ClassVar

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from splitmind_ai.app.logging_utils import preview_text
from splitmind_ai.memory.vault_store import VaultStore
from splitmind_ai.personas.loader import load_persona

logger = logging.getLogger(__name__)

# Defaults when vault has no prior state
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
        description="Normalize session input, load persona and persisted state from vault",
        reads=["request", "_internal"],
        writes=[
            "conversation",
            "persona",
            "relationship_state",
            "mood",
            "memory",
            "working_memory",
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
        vault_store: VaultStore | None = None,
        **services: Any,
    ) -> None:
        super().__init__(**services)
        self._persona_name = persona_name
        self._vault = vault_store

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

        # Load persisted state from vault (session start only)
        relationship_state = {
            "durable": dict(_DEFAULT_RELATIONSHIP_STATE["durable"]),
            "ephemeral": dict(_DEFAULT_RELATIONSHIP_STATE["ephemeral"]),
        }
        mood = dict(_DEFAULT_MOOD)
        memory: dict[str, Any] = {
            "session_summaries": [],
            "emotional_memories": [],
            "semantic_preferences": [],
        }

        if self._vault is not None:
            try:
                vault_rel = self._vault.load_relationship_state(user_id)
                if vault_rel:
                    for k, v in vault_rel.items():
                        if k in relationship_state["durable"]:
                            relationship_state["durable"][k] = v
                    logger.info("Loaded relationship state from vault for user=%s", user_id)
            except Exception:
                logger.warning("Failed to load relationship from vault", exc_info=True)

            try:
                vault_mood = self._vault.load_mood(user_id)
                if vault_mood:
                    for k, v in vault_mood.items():
                        if k in mood:
                            mood[k] = v
                    logger.info("Loaded mood state from vault for user=%s", user_id)
            except Exception:
                logger.warning("Failed to load mood from vault", exc_info=True)

            try:
                retrieval_params = _extract_memory_retrieval_params(request)
                has_targeted_retrieval = any(
                    value for key, value in retrieval_params.items() if key != "limit"
                )
                if has_targeted_retrieval:
                    memory = self._vault.retrieve_relevant_memories(user_id, **retrieval_params)
                    logger.info("Loaded targeted memory context for user=%s", user_id)
                else:
                    memory = self._vault.load_memory_context(user_id)
                logger.info(
                    "Loaded memory context: %d sessions, %d emotional, %d preferences",
                    len(memory.get("session_summaries", [])),
                    len(memory.get("emotional_memories", [])),
                    len(memory.get("semantic_preferences", [])),
                )
            except Exception:
                logger.warning("Failed to load memory from vault", exc_info=True)

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
            relationship_state=relationship_state,
            mood=mood,
            memory=memory,
            working_memory=working_memory,
            drive_state={},
            _internal=internal_update,
        )


def _default_persona_slice(persona_name: str) -> dict[str, Any]:
    return {
        "persona_version": 2,
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
        "limit": params.get("memory_limit", 3),
    }


def _derive_active_themes(memory: dict[str, Any]) -> list[str]:
    themes: list[str] = []
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
    for item in memory.get("emotional_memories", []):
        session_id = item.get("session_id")
        turn_number = item.get("turn_number")
        event = item.get("event")
        if session_id:
            ids.append(f"{session_id}:{turn_number or 0}")
        elif event:
            ids.append(event[:40])
    return ids[:5]
