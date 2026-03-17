"""Helpers for constructing OpenAI-compatible chat models from project settings."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from splitmind_ai.app.settings import Settings, load_settings

_UNSUPPORTED_CHAT_PARAMS_BY_TARGET = {
    "gpt-5.1-chat": {"temperature", "max_tokens"},
}


def _filtered_chat_kwargs(target: str, settings: Settings) -> dict[str, Any]:
    """Build common chat kwargs while filtering unsupported parameters."""
    kwargs: dict[str, Any] = {}
    if settings.llm.temperature is not None:
        kwargs["temperature"] = settings.llm.temperature
    if settings.llm.max_tokens is not None:
        kwargs["max_tokens"] = settings.llm.max_tokens

    unsupported = _UNSUPPORTED_CHAT_PARAMS_BY_TARGET.get(target.lower(), set())
    for key in unsupported:
        kwargs.pop(key, None)

    return kwargs


def azure_chat_openai_kwargs(settings: Settings) -> dict[str, Any]:
    """Build AzureChatOpenAI kwargs while filtering unsupported parameters."""
    kwargs = _filtered_chat_kwargs(settings.llm.azure_deployment, settings)
    kwargs.update(
        {
            "azure_deployment": settings.llm.azure_deployment,
            "api_version": settings.llm.api_version,
        }
    )
    return kwargs


def openai_chat_kwargs(settings: Settings) -> dict[str, Any]:
    """Build ChatOpenAI kwargs while filtering unsupported parameters."""
    kwargs = _filtered_chat_kwargs(settings.llm.model, settings)
    kwargs["model"] = settings.llm.model
    return kwargs


def create_chat_llm(settings: Settings | None = None) -> BaseChatModel:
    """Create a chat model from project settings."""
    resolved_settings = settings or load_settings()
    if resolved_settings.llm.provider == "openai":
        return ChatOpenAI(**openai_chat_kwargs(resolved_settings))
    return AzureChatOpenAI(**azure_chat_openai_kwargs(resolved_settings))
