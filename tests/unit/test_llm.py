"""Tests for chat model compatibility helpers."""

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from splitmind_ai.app.llm import (
    azure_chat_openai_kwargs,
    create_chat_llm,
    openai_chat_kwargs,
)
from splitmind_ai.app.settings import LLMSettings, Settings


def test_gpt_5_1_chat_filters_unsupported_temperature_and_max_tokens():
    settings = Settings(
        llm=LLMSettings(
            azure_deployment="gpt-5.1-chat",
            api_version="2024-12-01-preview",
            temperature=0.7,
            max_tokens=4096,
        )
    )

    kwargs = azure_chat_openai_kwargs(settings)

    assert kwargs == {
        "azure_deployment": "gpt-5.1-chat",
        "api_version": "2024-12-01-preview",
    }


def test_supported_azure_models_keep_temperature_and_max_tokens():
    settings = Settings(
        llm=LLMSettings(
            azure_deployment="gpt-4.1",
            api_version="2024-12-01-preview",
            temperature=0.3,
            max_tokens=2048,
        )
    )

    kwargs = azure_chat_openai_kwargs(settings)

    assert kwargs == {
        "azure_deployment": "gpt-4.1",
        "api_version": "2024-12-01-preview",
        "temperature": 0.3,
        "max_tokens": 2048,
    }


def test_openai_chat_kwargs_include_model_and_supported_params():
    settings = Settings(
        llm=LLMSettings(
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.2,
            max_tokens=512,
        )
    )

    kwargs = openai_chat_kwargs(settings)

    assert kwargs == {
        "model": "gpt-4.1-mini",
        "temperature": 0.2,
        "max_tokens": 512,
    }


def test_create_chat_llm_returns_chatopenai_for_openai_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings(
        llm=LLMSettings(
            provider="openai",
            model="gpt-4.1-mini",
        )
    )

    llm = create_chat_llm(settings)

    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "gpt-4.1-mini"


def test_create_chat_llm_returns_azure_model_for_azure_provider(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    settings = Settings(
        llm=LLMSettings(
            provider="azure",
            azure_deployment="gpt-4.1",
            api_version="2024-12-01-preview",
        )
    )

    llm = create_chat_llm(settings)

    assert isinstance(llm, AzureChatOpenAI)
    assert llm.deployment_name == "gpt-4.1"
