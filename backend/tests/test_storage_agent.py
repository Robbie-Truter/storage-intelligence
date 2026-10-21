"""Tests for the read-only agent.

Covers the tool map the agent is given, the cap on how many steps it may take,
and what ``run_readonly_analysis`` reports back. No LLM credentials are
needed: the chat model is a fake with fixed replies, and the tools are local
stubs that behave like the MCP tools - a structured answer, a reported error,
and a broken connection.
"""

from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from storage_intelligence_backend.agents import storage_agent
from storage_intelligence_backend.agents.storage_agent import (
    build_agent,
    run_readonly_analysis,
)
from storage_intelligence_backend.mcp.errors import MCPUnavailable
from storage_intelligence_backend.mcp.manager import (
    READONLY_TOOL_ALLOWLIST,
    StorageMCPClient,
)


class _StubInput(BaseModel):
    """Input schema for the stub tools."""

    path: str = ""


class FakeChatModel(GenericFakeChatModel):
    """A fake chat model with fixed replies that records what it was asked.

    ``GenericFakeChatModel`` does not implement ``bind_tools``, which the agent
    calls, so it is added here.
    """

    asked: list[list[BaseMessage]] = Field(default_factory=list)

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
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
    ``allowlisted_tools``, so the allowlist is applied when the manager hands
    the catalogue out.
    """

    def __init__(self, tools: dict[str, BaseTool] | None = None) -> None:
        super().__init__(command="", args=[], project_directory="")
        self._langchain_tools = dict(tools or {})


def _stub_tool(name: str) -> BaseTool:
    """A tool that only has to exist."""

    async def call(**_: Any) -> str:
        return "done"

    return StructuredTool(
        name=name,
        description=f"stub {name}",
        args_schema=_StubInput,
        coroutine=call,
    )


def _structured_tool(name: str, payload: dict[str, Any]) -> BaseTool:
    """A tool that answers with a structured payload, like the MCP tools do."""

    async def call(**_: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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

    A reported error is handed back to the agent as a failed tool call; a
    broken connection is not something the agent can act on, so it travels on.
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

    The manager applies the allowlist as it hands the catalogue out, so the
    agent is given exactly these.
    """
    return {name: _stub_tool(name) for name in READONLY_TOOL_ALLOWLIST}


def test_agent_is_given_only_the_allowlisted_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(monkeypatch, AIMessage(content="done"))
    manager = FakeManager(tools=_allowed_tools())

    agent = build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0.0,
        max_iterations=10,
    )

    given = set(agent.nodes["tools"].bound.tools_by_name)
    assert given == set(READONLY_TOOL_ALLOWLIST)
    assert "trash_path" not in given


async def test_agent_stops_when_it_runs_out_of_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = [
        _tool_call("find_large_files", {"path": "/data"}, f"c{i}") for i in range(20)
    ]
    _fake_model(monkeypatch, *replies)
    manager = FakeManager(
        tools={"find_large_files": _structured_tool("find_large_files", {})}
    )

    agent = build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0.0,
        max_iterations=4,
    )

    with pytest.raises(GraphRecursionError):
        await agent.ainvoke({"messages": [{"role": "user", "content": "go"}]})


async def test_analysis_reports_the_tools_it_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _fake_model(
        monkeypatch,
        _tool_call("find_large_files", {"path": "/data"}),
        AIMessage(content="The biggest file is /data/a."),
    )
    manager = FakeManager(
        tools={
            "find_large_files": _structured_tool(
                "find_large_files", {"files": [{"path": "/data/a", "size_bytes": 10}]}
            )
        }
    )

    agent = build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0.0,
        max_iterations=10,
    )

    result = await run_readonly_analysis(agent, "/data", "What is biggest?")

    assert result["summary"] == "The biggest file is /data/a."
    assert result["tool_calls"] == [
        {
            "name": "find_large_files",
            "args": {"path": "/data"},
            "status": "ok",
            "result": {"files": [{"path": "/data/a", "size_bytes": 10}]},
        }
    ]
    assert "What is biggest?" in model.asked[0][-1].content
    assert "/data" in model.asked[0][-1].content


async def test_analysis_records_a_tool_that_reported_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(
        monkeypatch,
        _tool_call("file_info", {"path": "/data/missing"}),
        AIMessage(content="That file is not there."),
    )
    manager = FakeManager(
        tools={"file_info": _failing_tool("file_info", ToolException("no such file"))}
    )

    agent = build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0.0,
        max_iterations=10,
    )

    result = await run_readonly_analysis(agent, "/data")

    assert result["summary"] == "That file is not there."
    assert result["tool_calls"] == [
        {
            "name": "file_info",
            "args": {"path": "/data/missing"},
            "status": "error",
            "result": "no such file",
        }
    ]


async def test_analysis_reports_a_broken_connection_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_model(
        monkeypatch,
        _tool_call("file_info", {"path": "/data"}),
        AIMessage(content="never reached"),
    )
    manager = FakeManager(
        tools={
            "file_info": _failing_tool(
                "file_info", ConnectionResetError("MCP pipe closed")
            )
        }
    )

    agent = build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0.0,
        max_iterations=10,
    )

    with pytest.raises(MCPUnavailable):
        await run_readonly_analysis(agent, "/data")


async def test_analysis_reports_the_step_cap_as_it_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = [
        _tool_call("find_large_files", {"path": "/data"}, f"c{i}") for i in range(20)
    ]
    _fake_model(monkeypatch, *replies)
    manager = FakeManager(
        tools={"find_large_files": _structured_tool("find_large_files", {})}
    )

    agent = build_agent(
        model="openai:gpt-4.1",
        manager=manager,
        temperature=0.0,
        max_iterations=4,
    )

    with pytest.raises(GraphRecursionError):
        await run_readonly_analysis(agent, "/data")
