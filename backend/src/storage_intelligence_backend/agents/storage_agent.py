"""Read-only LangChain agent over an explicit allowlist of MCP tools.

The tool catalogue comes from the manager, which hands over only the tools in
``READONLY_TOOL_ALLOWLIST`` (including the MCP server's ``preview_trash``
tool); the raw ``trash_path`` tool is never among them. The allowlist is the
manager's business - see ``StorageMCPClient.langchain_tools``.
"""

from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from storage_intelligence_backend.mcp.errors import MCPError, MCPUnavailable
from storage_intelligence_backend.mcp.manager import StorageMCPClient


def build_agent(
    model: str,
    manager: StorageMCPClient,
    temperature: float,
    max_iterations: int,
    *,
    api_key: str | None = None,
) -> Any:
    """Build a read-only agent from the tools the manager offers.

    The tools come from ``manager.langchain_tools``, which applies the
    read-only allowlist: only the allowlisted tools - ``preview_trash``
    included - are bound to the model, and the raw ``trash_path`` tool is
    never among them.

    ``api_key`` is the client-supplied provider key; it is passed to the
    provider constructor when given and is never stored.

    ``max_iterations`` caps how many times the agent may loop: ask the model,
    run a tool, ask again. The cap counts each of those steps separately, so
    one round trip through a tool uses two of them. When the cap is reached
    the run stops with ``GraphRecursionError`` instead of looping forever.
    """
    if api_key:
        llm = init_chat_model(model, temperature=temperature, api_key=api_key)
    else:
        llm = init_chat_model(model, temperature=temperature)

    tools = list(manager.langchain_tools.values())

    agent = create_agent(
        model=llm,
        tools=tools,
    )

    return agent.with_config({"recursion_limit": max_iterations})


async def run_readonly_analysis(
    agent: Any,
    path: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    """Ask the agent about ``path`` and report back what it did.

    ``path`` and ``question`` are both optional: without a path the agent
    investigates the default location - the home directory the MCP tools fall
    back to - and without a question it looks for what takes the most space.

    Returns the agent's final answer as ``summary``, and one record per tool
    call as ``tool_calls``. Each record has the tool ``name``, the ``args`` it
    was called with, a ``status`` of ``ok`` or ``error``, and the ``result``.

    The result is the tool's structured answer, which the MCP tools keep next
    to the shortened text the model reads; the text is only used when a tool
    reported an error and has no structured answer. A tool that reported an
    error is recorded as failed - the agent carried on and answered anyway.
    If the connection to the MCP server breaks, the run cannot finish and
    ``MCPUnavailable`` is raised, which the app turns into a 503.

    Raises:
        MCPUnavailable: The connection to the MCP server broke during the run.
        GraphRecursionError: The agent used up its steps without finishing.
    """
    prompt = _build_prompt(path, question)

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )
    except (MCPError, GraphRecursionError):
        raise
    except Exception as exc:
        raise MCPUnavailable(f"Agent run failed: {exc}") from exc

    messages = result.get("messages", [])
    return {
        "summary": _final_summary(messages),
        "tool_calls": _tool_call_records(messages),
    }


def _build_prompt(path: str | None = None, question: str | None = None) -> str:
    """The question sent to the agent; the path is part of it when there is one.

    A path and a question are combined - the question first, the target path
    below it. A question on its own is sent as it is. Without a path the agent
    is pointed at the default location, which is where the MCP tools start
    when the model leaves their ``path`` argument out.
    """
    if question and question.strip():
        if path:
            return f"{question.strip()}\n\nTarget path: {path}"
        return question.strip()

    if path:
        return (
            f"Analyze the storage usage under {path} and report what takes the most "
            "space."
        )
    return (
        "Analyze the storage usage starting from the default location and report what "
        "takes the most space."
    )


def _final_summary(messages: list[Any]) -> str:
    """The agent's last spoken answer, or an empty string."""
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.text.strip():
            return message.text.strip()
    return ""


def _tool_call_records(messages: list[Any]) -> list[dict[str, Any]]:
    """One record per tool call, in the order the agent made them."""
    calls: dict[str, Any] = {}
    for message in messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                call_id = call.get("id")
                if call_id:
                    calls[call_id] = call

    records: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        call = calls.get(message.tool_call_id)
        records.append(
            {
                "name": call["name"] if call else message.name,
                "args": call["args"] if call else {},
                "status": "error" if message.status == "error" else "ok",
                "result": _tool_result(message),
            }
        )
    return records


def _tool_result(message: ToolMessage) -> Any:
    """The structured answer of a tool call, or its text when there is none."""
    artifact = message.artifact
    if isinstance(artifact, dict):
        structured = artifact.get("structured_content")
        if structured is not None:
            return structured
    return _content_text(message.content)


def _content_text(content: Any) -> str:
    """Flatten message content (a string or content blocks) into a string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(part for part in parts if part)
    return str(content)
