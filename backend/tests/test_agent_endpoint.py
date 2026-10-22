"""Tests for ``POST /api/agent/analyze``.

The MCP manager and the chat model are both fakes, so no subprocess is spawned
and no LLM credentials are needed. The fake manager hands over a tool
catalogue and the fake model answers with fixed replies.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from storage_intelligence_backend.agents import storage_agent
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
    return {
        name: _structured_tool(name, TOOL_RESULT) for name in READONLY_TOOL_ALLOWLIST
    }


def _agent_client(fake_manager: FakeManager) -> TestClient:
    """App wired to ``fake_manager``; lifespan is not entered (no subprocess)."""
    app = create_app()
    app.state.mcp = None
    app.dependency_overrides[get_mcp_manager] = lambda: fake_manager
    return TestClient(app)


def test_analyze_returns_the_summary_and_the_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(
        monkeypatch,
        _tool_call("find_large_files", {"path": "/tmp"}),
        AIMessage(content="The biggest file is /tmp/a."),
    )
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post("/api/agent/analyze", json={"path": "/tmp"})

    assert response.status_code == 200
    assert response.json() == {
        "summary": "The biggest file is /tmp/a.",
        "tool_calls": [
            {
                "name": "find_large_files",
                "args": {"path": "/tmp"},
                "status": "ok",
                "result": TOOL_RESULT,
            }
        ],
    }


def test_analyze_without_a_question_asks_about_the_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="Nothing big here."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post("/api/agent/analyze", json={"path": "/tmp"})

    assert response.status_code == 200
    assert response.json()["summary"] == "Nothing big here."
    assert "/tmp" in model.asked[0][-1].content


def test_analyze_sends_the_question_and_the_path_to_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="The biggest file is /tmp/a."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze", json={"path": "/tmp", "question": "What is biggest?"}
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

    response = _agent_client(manager).post("/api/agent/analyze", json={})

    assert response.status_code == 200
    assert response.json()["summary"] == "Nothing big here."
    prompt = model.asked[0][-1].content
    assert "default location" in prompt
    assert "Target path" not in prompt


def test_analyze_with_only_a_question_keeps_the_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(monkeypatch, AIMessage(content="Nothing big here."))
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post(
        "/api/agent/analyze", json={"question": "What is biggest?"}
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Nothing big here."
    assert model.asked[0][-1].content == "What is biggest?"


def test_analyze_without_an_mcp_manager_returns_503(client: TestClient) -> None:
    response = client.post("/api/agent/analyze", json={"path": "/tmp"})

    assert response.status_code == 503
    assert response.json() == {"detail": "MCP server is not available"}


def test_analyze_when_the_connection_breaks_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(
        monkeypatch,
        _tool_call("file_info", {"path": "/tmp"}),
        AIMessage(content="never reached"),
    )
    manager = FakeManager(
        tools={
            "file_info": _failing_tool(
                "file_info", ConnectionResetError("MCP pipe closed")
            )
        }
    )

    response = _agent_client(manager).post("/api/agent/analyze", json={"path": "/tmp"})

    assert response.status_code == 503
    assert "MCP pipe closed" in response.json()["detail"]


def test_analyze_when_the_step_cap_is_reached_returns_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = [
        _tool_call("find_large_files", {"path": "/tmp"}, f"c{i}") for i in range(20)
    ]
    _fake_model(monkeypatch, *replies)
    monkeypatch.setattr(
        agent_router, "get_settings", lambda: Settings(agent_max_iterations=4)
    )
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post("/api/agent/analyze", json={"path": "/tmp"})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "4" in detail
    assert "step" in detail.lower()


def test_analyze_when_the_model_cannot_be_built_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError("OPENAI_API_KEY is not set")

    monkeypatch.setattr(storage_agent, "init_chat_model", _boom)
    manager = FakeManager(tools=_allowed_tools())

    response = _agent_client(manager).post("/api/agent/analyze", json={"path": "/tmp"})

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

    response = _agent_client(manager).post("/api/agent/analyze", json={"path": "/tmp"})

    assert response.status_code == 200
    body = response.json()

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
    assert all(call["name"] != "trash_path" for call in body["tool_calls"])
