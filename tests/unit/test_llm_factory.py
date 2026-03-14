"""Tests for llm/factory.py."""

import pytest


def test_unknown_provider_raises_value_error():
    from yt_agent.llm.factory import create_llm

    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_llm("unknown_provider")  # type: ignore[arg-type]


def test_factory_creates_claude_llm(monkeypatch):
    import yt_agent.config as config_module
    from yt_agent.llm.claude import ClaudeLLM
    from yt_agent.llm.factory import create_llm

    monkeypatch.setattr(config_module.settings, "anthropic_api_key", "test-key")
    result = create_llm("claude")
    assert isinstance(result, ClaudeLLM)


def test_factory_creates_openai_llm(monkeypatch):
    import yt_agent.config as config_module
    from yt_agent.llm.factory import create_llm
    from yt_agent.llm.openai import OpenAILLM

    monkeypatch.setattr(config_module.settings, "openai_api_key", "test-key")
    result = create_llm("openai")
    assert isinstance(result, OpenAILLM)


def test_factory_uses_default_provider(monkeypatch):
    import yt_agent.config as config_module
    from yt_agent.llm.claude import ClaudeLLM
    from yt_agent.llm.factory import create_llm

    monkeypatch.setattr(config_module.settings, "default_llm_provider", "claude")
    monkeypatch.setattr(config_module.settings, "anthropic_api_key", "test-key")
    result = create_llm()
    assert isinstance(result, ClaudeLLM)


def test_claude_raises_without_api_key(monkeypatch):
    import yt_agent.config as config_module
    from yt_agent.llm.factory import create_llm

    monkeypatch.setattr(config_module.settings, "anthropic_api_key", None)
    with pytest.raises(ValueError, match="Anthropic API key"):
        create_llm("claude")
