"""Tests for ``POST /api/agent/analyze``.

The MCP manager and the chat model are both fakes, so no subprocess is spawned
and no LLM credentials are needed. The fake manager hands over a tool
catalogue and the fake model answers with fixed replies.
"""

import asyncio
import contextlib
import json
import re
from collections.abc import Iterator
from dataclasses import asdict
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from storage_intelligence_backend.agents import storage_agent
from storage_intelligence_backend.agents.models import MODEL_CATALOG
from storage_intelligence_backend.config import Settings
from storage_intelligence_backend.deps import get_mcp_manager
from storage_intelligence_backend.main import create_app
from storage_intelligence_backend.mcp.manager import (
    READONLY_TOOL_ALLOWLIST,
    StorageMCPClient,
)
from storage_intelligence_backend.routers import agent as agent_router

TOOL_RESULT: dict[str, Any] = {"files": [{"path": "/tmp/a", "size_bytes": 10}]}


class _StubInput(BaseModel):
    """Input schema for the stub tools."""

    path: str = ""


class FakeChatModel(GenericFakeChatModel):
    """A fake chat model with fixed replies that records what it was asked.

    ``GenericFakeChatModel`` does not implement ``bind_tools``, which the agent
    calls, so it is added here. It also records the names of the tools that
    were bound to it - that is how the safety test sees which tools the model
    could reach at all.
    """

    asked: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[list[str]] = Field(default_factory=list)

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        self.bound_tools.append([tool.name for tool in tools])
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.asked.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream tool-call replies too; the base fake drops empty content."""
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        message = result.generations[0].message
        if isinstance(message, AIMessage) and message.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "name": call["name"],
                            "args": json.dumps(call["args"]),
                            "id": call["id"],
                            "index": index,
                            "type": "tool_call_chunk",
                        }
                        for index, call in enumerate(message.tool_calls)
                    ],
                )
            )
            return
        content = message.content if isinstance(message, AIMessage) else ""
        if isinstance(content, str) and content:
            for token in re.split(r"(\s)", content):
                chunk = ChatGenerationChunk(
                    message=AIMessageChunk(content=token, id=message.id)
                )
                if run_manager:
                    run_manager.on_llm_new_token(token, chunk=chunk)
                yield chunk


class FakeManager(StorageMCPClient):
    """Stands in for ``StorageMCPClient``; hands out a fixed tool catalogue.

    The tools go straight into the manager's state, without passing through
    ``allowlisted_tools``, so the tests can check that the allowlist is
    enforced when the catalogue is handed out.
    """

    def __init__(self, tools: dict[str, BaseTool] | None = None) -> None:
        super().__init__(command="", args=[], project_directory="")
        self._langchain_tools = dict(tools or {})

    @property
    def state_tools(self) -> dict[str, BaseTool]:
        """The tools the manager holds, before the allowlist is applied."""
        return dict(self._langchain_tools)


def _structured_tool(
    name: str,
    payload: dict[str, Any],
    calls: list[dict[str, Any]] | None = None,
) -> BaseTool:
    """A tool that answers with a structured payload, like the MCP tools do.

    When ``calls`` is given, every call is recorded in it.
    """

    async def call(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if calls is not None:
            calls.append(kwargs)
        return ([{"type": "text", "text": "done"}], {"structured_content": payload})

    return StructuredTool(
        name=name,
        description=f"stub {name}",
        args_schema=_StubInput,
        coroutine=call,
        response_format="content_and_artifact",
    )


def _failing_tool(name: str, error: Exception) -> BaseTool:
    """A tool that fails, the way the MCP tools fail.

    A broken connection is not something the agent can act on, so it travels
    on and the run cannot finish.
    """

    async def call(**_: Any) -> str:
        raise error

    return StructuredTool(
        name=name,
        description=f"stub {name}",
        args_schema=_StubInput,
        coroutine=call,
        handle_tool_error=lambda exc: str(exc),
    )


def _tool_call(name: str, args: dict[str, Any], call_id: str = "c1") -> AIMessage:
    """A reply in which the agent asks for a tool."""
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _fake_model(monkeypatch: pytest.MonkeyPatch, *replies: AIMessage) -> FakeChatModel:
    """Make ``build_agent`` use a fake chat model, so no LLM keys are needed."""
    model = FakeChatModel(messages=iter(replies))
    monkeypatch.setattr(storage_agent, "init_chat_model", lambda *a, **k: model)
    return model


def _allowed_tools() -> dict[str, BaseTool]:
    """The catalogue the manager hands over: the allowlisted tools.

    The manager filters the MCP tools to the allowlist when it opens the
    connection, so the agent is given exactly these.
    """
    return {name: _structured_tool(name, TOOL_RESULT) for name in READONLY_TOOL_ALLOWLIST}


def _agent_client(fake_manager: FakeManager) -> TestClient:
    """App wired to ``fake_manager``; lifespan is not entered (no subprocess)."""
    app = create_app()
    app.state.mcp = None
    app.dependency_overrides[get_mcp_manager] = lambda: fake_manager
    return TestClient(app)


def _user_messages(text: str) -> list[dict[str, Any]]:
    """A one-message history in the Vercel AI SDK UIMessage shape.

    An empty ``text`` is what the frontend sends for a run without a
    question; the backend then falls back to its default question.
    """
    return [{"id": "m1", "role": "user", "parts": [{"type": "text", "text": text}]}]


def _sse_events(response: Any) -> list[dict[str, Any]]:
    """The ``data`` payload of every SSE frame, in order.

    The ``[DONE]`` sentinel that ends the stream is not JSON, so it is
    skipped.
    """
    return [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


def _summary(response: Any) -> str:
    """The answer text, reassembled from the ``text-delta`` frames."""
    return "".join(
        event["delta"] for event in _sse_events(response) if event.get("type") == "text-delta"
    )


def _tool_calls(response: Any) -> list[dict[str, Any]]:
    """The tool calls the stream reported, from the input/output frame pairs."""
    events = _sse_events(response)
    inputs = [event for event in events if event.get("type") == "tool-input-available"]
    outputs = {
        event["toolCallId"]: event
        for event in events
        if event.get("type") == "tool-output-available"
    }
    return [
        {
            "name": event["toolName"],
            "args": event["input"],
            "output": outputs.get(event["toolCallId"], {}).get("output"),
        }
        for event in inputs
    ]


def _error(response: Any) -> str:
    """The text of the single ``error`` event of a failed stream."""
    events = _sse_events(response)
    errors = [event for event in events if event.get("type") == "error"]
    assert errors, events
    return errors[-1]["errorText"]


def test_models_lists_the_catalog_without_mcp_or_credentials(
    client: TestClient,
) -> None:
    response = client.get("/api/agent/models")

    assert response.status_code == 200
    assert response.json() == [asdict(option) for option in MODEL_CATALOG]
    assert response.json()


def test_analyze_rejects_missing_provider_or_model_name() -> None:
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post("/api/agent/analyze", json={"model": "not-a-model"})

    assert response.status_code == 422


def test_analyze_accepts_a_custom_model_for_a_supported_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeChatModel(messages=iter([AIMessage(content="Nothing big here.")]))
    selected: list[str] = []
    captured: dict[str, Any] = {}

    def _init_chat_model(model: str, **kwargs: Any) -> FakeChatModel:
        selected.append(model)
        captured.update(kwargs)
        return fake_model

    monkeypatch.setattr(storage_agent, "init_chat_model", _init_chat_model)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "model": "custom-openai-gpt-4o",
            "provider": "openai",
            "model_name": "gpt-4o",
            "api_key": "client-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert selected == ["openai:gpt-4o"]
    assert captured["api_key"] == "client-key"


def test_analyze_rejects_a_custom_model_for_an_unsupported_provider() -> None:
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "model": "custom-anthropic-claude",
            "provider": "anthropic",
            "model_name": "claude-sonnet",
            "api_key": "client-key",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "anthropic" in detail
    assert "openai" in detail


def test_analyze_rejects_a_custom_model_without_a_name() -> None:
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "model": "custom-openai-empty",
            "provider": "openai",
            "model_name": "   ",
            "api_key": "client-key",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 422
    assert "model_name" in response.json()["detail"]


def test_analyze_uses_the_model_selected_in_the_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeChatModel(messages=iter([AIMessage(content="Nothing big here.")]))
    selected: list[str] = []
    captured: dict[str, Any] = {}

    def _init_chat_model(model: str, **kwargs: Any) -> FakeChatModel:
        selected.append(model)
        captured.update(kwargs)
        return fake_model

    monkeypatch.setattr(storage_agent, "init_chat_model", _init_chat_model)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "google_genai",
            "model_name": "gemini-2.5-flash",
            "model": "google-gemini-2.5-flash",
            "api_key": "client-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert selected == ["google_genai:gemini-2.5-flash"]
    assert captured["api_key"] == "client-key"


def test_analyze_requires_an_api_key_for_cloud_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_router, "stored_api_key", lambda _provider: None)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 422
    assert "api_key" in response.json()["detail"]


def test_analyze_allows_ollama_without_an_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeChatModel(messages=iter([AIMessage(content="Nothing big here.")]))
    captured: dict[str, Any] = {}

    def _init_chat_model(model: str, **kwargs: Any) -> FakeChatModel:
        captured["model"] = model
        captured.update(kwargs)
        return fake_model

    monkeypatch.setattr(storage_agent, "init_chat_model", _init_chat_model)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "ollama",
            "model_name": "llama3.1",
            "model": "ollama-llama3.1",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert captured["model"] == "ollama:llama3.1"
    assert "api_key" not in captured


def test_analyze_returns_the_summary_and_the_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(
        monkeypatch,
        _tool_call("find_large_files", {"path": "/tmp"}),
        AIMessage(content="The biggest file is /tmp/a."),
    )
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert _summary(response) == "The biggest file is /tmp/a."
    assert _tool_calls(response) == [
        {
            "name": "find_large_files",
            "args": {"path": "/tmp"},
            "output": [{"type": "text", "text": "done"}],
        }
    ]


def test_analyze_without_a_question_asks_about_the_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="Nothing big here."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert _summary(response) == "Nothing big here."
    assert "/tmp" in model.asked[0][-1].content


def test_analyze_sends_the_question_and_the_path_to_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="The biggest file is /tmp/a."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages("What is biggest?"),
        },
    )

    assert response.status_code == 200
    prompt = model.asked[0][-1].content
    assert "What is biggest?" in prompt
    assert "/tmp" in prompt


def test_analyze_without_a_path_asks_about_the_default_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="Nothing big here."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert _summary(response) == "Nothing big here."
    prompt = model.asked[0][-1].content
    assert "default path" in prompt
    assert "Target path" in prompt


def test_analyze_with_only_a_question_keeps_the_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="Nothing big here."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "messages": _user_messages("What is biggest?"),
        },
    )

    assert response.status_code == 200
    assert _summary(response) == "Nothing big here."
    assert "What is biggest?" in model.asked[0][-1].content


def test_analyze_without_an_mcp_manager_returns_503(client: TestClient) -> None:
    response = client.post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "MCP server is not available"}


def test_analyze_when_the_connection_breaks_streams_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(
        monkeypatch,
        _tool_call("file_info", {"path": "/tmp"}),
        AIMessage(content="never reached"),
    )
    manager = FakeManager(
        tools={
            "file_info": _failing_tool("file_info", ConnectionResetError("MCP pipe closed"))
        }
    )

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert "MCP pipe closed" in _error(response)


def test_analyze_when_the_step_cap_is_reached_streams_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = [_tool_call("find_large_files", {"path": "/tmp"}, f"c{i}") for i in range(20)]
    _fake_model(monkeypatch, *replies)
    monkeypatch.setattr(agent_router, "get_settings", lambda: Settings(agent_max_iterations=4))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    detail = _error(response)
    assert "4" in detail
    assert "step" in detail.lower()


def test_analyze_when_the_model_cannot_be_built_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError("OPENAI_API_KEY is not set")

    monkeypatch.setattr(storage_agent, "init_chat_model", _boom)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "OPENAI_API_KEY" in detail


def test_analyze_never_binds_or_calls_trash_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trash_calls: list[dict[str, Any]] = []
    tools = _allowed_tools()
    tools["trash_path"] = _structured_tool("trash_path", {}, calls=trash_calls)

    model = _fake_model(
        monkeypatch,
        _tool_call("find_large_files", {"path": "/tmp"}),
        AIMessage(content="The biggest file is /tmp/a."),
    )
    manager = FakeManager(tools=tools)

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    tool_calls = _tool_calls(response)

    # The manager holds the raw trash_path tool ...
    assert "trash_path" in manager.state_tools
    # ... but it was never bound to the model ...
    bound = set(model.bound_tools[0])
    assert bound == set(READONLY_TOOL_ALLOWLIST)
    assert "trash_path" not in bound
    # ... it was never invoked ...
    assert trash_calls == []
    # ... and it shows up nowhere in the answer. preview_trash is the only
    # trash-related tool the agent can reach.
    assert "preview_trash" in bound
    assert all(call["name"] != "trash_path" for call in tool_calls)


def test_analyze_when_gemini_is_overloaded_streams_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _failing_generate(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("503 The model is overloaded. Please try again later.")

    model = _fake_model(monkeypatch)
    monkeypatch.setattr(model, "_generate", _failing_generate)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "google_genai",
            "model_name": "gemini-2.5-flash",
            "model": "google-gemini-2.5-flash",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert (
        _error(response)
        == "The AI model is currently overloaded. Please try again in a few moments."
    )


def test_analyze_when_quota_exhausted_streams_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _failing_generate(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("429 Resource has been exhausted (e.g. check quota)")

    model = _fake_model(monkeypatch)
    monkeypatch.setattr(model, "_generate", _failing_generate)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert _error(response) == (
        "The AI model rate limit or quota has been exceeded. "
        "Please check your provider quota or try again later."
    )


def test_analyze_when_api_key_invalid_streams_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _failing_generate(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("401 Invalid API key provided")

    model = _fake_model(monkeypatch)
    monkeypatch.setattr(model, "_generate", _failing_generate)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1",
            "model": "openai-gpt-4.1",
            "api_key": "test-key",
            "path": "/tmp",
            "messages": _user_messages(""),
        },
    )

    assert response.status_code == 200
    assert _error(response) == "Invalid API key provided for the model provider."


async def test_agent_event_stream_cancels_the_run_when_the_consumer_disconnects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A client disconnect must cancel the agent run, not orphan it.

    The consumer task plays the part Starlette plays when the browser aborts
    the request: it is cancelled mid-stream, and that cancellation has to
    travel into the tool the agent is blocked on. The endpoint generator
    owns the run in a task of its own, so a disconnect cancels it instead of
    leaving it to finish in the background.
    """
    _fake_model(
        monkeypatch,
        _tool_call("find_large_files", {"path": "/tmp"}),
        AIMessage(content="never reached"),
    )

    tool_cancelled = asyncio.Event()

    async def call(**_: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            tool_cancelled.set()
            raise
        return ([{"type": "text", "text": "done"}], {"structured_content": TOOL_RESULT})

    blocking_tool = StructuredTool(
        name="find_large_files",
        description="stub find_large_files",
        args_schema=_StubInput,
        coroutine=call,
        response_format="content_and_artifact",
    )

    manager = FakeManager(tools={"find_large_files": blocking_tool})
    agent = storage_agent.build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0,
        max_iterations=8,
    )

    frames: list[str] = []

    async def consume() -> None:
        async for frame in agent_router._agent_event_stream(
            agent, "/tmp", None, max_iterations=8
        ):
            frames.append(frame)

    async def wait_for_tool_frame() -> None:
        while not any("tool-input-available" in frame for frame in frames):
            await asyncio.sleep(0.01)

    consumer = asyncio.create_task(consume())
    await asyncio.wait_for(wait_for_tool_frame(), timeout=10)
    consumer.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await consumer

    await asyncio.wait_for(tool_cancelled.wait(), timeout=10)
