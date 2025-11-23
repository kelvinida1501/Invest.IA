from types import SimpleNamespace

import pytest

from app.services import chat_agent


class DummyHuman:
    def __init__(self, content: str):
        self.content = content


class DummyAI:
    def __init__(self, content: str):
        self.content = content


class DummySystem:
    def __init__(self, content: str):
        self.content = content


class DummyPromptValue:
    def __init__(self, messages):
        self._messages = messages

    def to_messages(self):
        return self._messages


class DummyResponse:
    def __init__(self, json_payload):
        self._payload = json_payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyHttpClient:
    def __init__(self, payload):
        self.payload = payload
        self.last_json = None

    def post(self, url, json):
        self.last_json = json
        return DummyResponse(self.payload)


def _base_settings():
    return SimpleNamespace(
        llm=SimpleNamespace(
            provider="openai",
            api_key="test-key",
            api_base="https://api.test",
            request_timeout=5.0,
            model="gpt-test",
            temperature=0.1,
            max_output_tokens=50,
        )
    )


def test_create_http_client_skips_when_provider_not_openai(monkeypatch):
    agent = object.__new__(chat_agent.ChatAgent)
    agent._settings = SimpleNamespace(llm=SimpleNamespace(provider="anthropic"))
    assert agent._create_http_client() is None


def test_create_http_client_skips_when_api_key_missing(monkeypatch):
    agent = object.__new__(chat_agent.ChatAgent)
    agent._settings = SimpleNamespace(
        llm=SimpleNamespace(
            provider="openai",
            api_key="",
            api_base="https://api.test",
            request_timeout=5,
            model="gpt-test",
            temperature=0.1,
            max_output_tokens=50,
        )
    )
    assert agent._create_http_client() is None


def test_invoke_openai_happy_path(monkeypatch):
    # força classes de mensagens simples
    monkeypatch.setattr(chat_agent, "HumanMessage", DummyHuman)
    monkeypatch.setattr(chat_agent, "AIMessage", DummyAI)
    monkeypatch.setattr(chat_agent, "SystemMessage", DummySystem)
    monkeypatch.setattr(chat_agent, "BaseMessage", object)

    agent = object.__new__(chat_agent.ChatAgent)
    agent._settings = _base_settings()
    client = DummyHttpClient({"choices": [{"message": {"content": " resposta "}}]})
    agent._http_client = client

    prompt_value = DummyPromptValue(
        [DummySystem("s"), DummyHuman("u"), DummyAI("a")]
    )

    reply = agent._invoke_openai(prompt_value)
    assert reply == "resposta"
    assert client.last_json["messages"][0]["role"] == "system"


def test_invoke_openai_requires_choices(monkeypatch):
    monkeypatch.setattr(chat_agent, "HumanMessage", DummyHuman)
    monkeypatch.setattr(chat_agent, "AIMessage", DummyAI)
    monkeypatch.setattr(chat_agent, "SystemMessage", DummySystem)
    monkeypatch.setattr(chat_agent, "BaseMessage", object)

    agent = object.__new__(chat_agent.ChatAgent)
    agent._settings = _base_settings()
    agent._http_client = DummyHttpClient({"choices": []})

    prompt_value = DummyPromptValue([DummyHuman("hi")])

    with pytest.raises(ValueError):
        agent._invoke_openai(prompt_value)

