"""Read-only LangChain agent over an explicit allowlist of MCP tools.

The tool catalogue comes from the manager, which hands over only the tools in
``READONLY_TOOL_ALLOWLIST`` (including the MCP server's ``preview_trash``
tool); the raw ``trash_path`` tool is never among them. The allowlist is the
manager's business - see ``StorageMCPClient.langchain_tools``.
"""

import os
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from storage_intelligence_backend.mcp.errors import MCPError, MCPUnavailable
from storage_intelligence_backend.mcp.manager import StorageMCPClient

TOOL_USAGE_RULES = (
    "Tool usage rules:\n"
    "- Only use filesystem tools for requests involving storage analysis or file management. "
    "For greetings, general knowledge, programming, weather or unrelated requests, "
    "respond without calling tools and briefly explain the agent's scope when appropriate.\n"
    "- A supplied target path does not automatically require filesystem inspection.\n"
    "- Do not make tool calls merely to gather context when the request can be answered "
    "without filesystem access.\n"
    "- Use explore_directory for lightweight directory discovery when the relevant "
    "location is unknown. Identify relevant directories first, then run specialized "
    "analysis tools on the narrowest appropriate path. Avoid recursive directory "
    "exploration unless explicitly needed.\n"
    "- Use directory_disk_usage when a size breakdown or largest-item ranking is needed. "
    "It recursively calculates the size of each immediate child directory, so avoid "
    "running it on broad locations such as the home directory unless that overview "
    "is necessary. Do not automatically drill down or repeat scans on nested paths. "
    "Investigate further only when explicitly requested or necessary to answer "
    "a specific question.\n"
    "- Stop calling tools once the available results answer the request.\n"
    "- Never recommend deleting something solely because it is large, old, unused "
    "or classified as junk. Establish its purpose and potential impact first. "
    "If uncertain, explain the risk and advise against deletion until verified.\n"
    "- Explain the consequences of destructive cleanup commands. Treat databases, "
    "backups, virtual disks and persistent volumes as potentially important data.\n"
)


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
        system_prompt=TOOL_USAGE_RULES,
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
        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
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
    """Build the complete prompt sent to the storage analysis agent.

    Combines the tool usage rules with the user's request. If a question is
    provided, it is used as the main request. Otherwise, a default storage
    analysis request is generated.

    When a target path is provided, it is appended as additional context
    for filesystem-related operations. Its presence does not imply that
    filesystem tools should be used.

    The tool usage rules are included before the user's request to guide
    the agent's decisions about when filesystem tools are appropriate.
    """
    if path is None or (isinstance(path, str) and not path.strip()):
        home_directory = os.path.expanduser("~")
        path = (
            f"{home_directory} (This is default path since user did not supply any, "
            "only use it for analysis if user asks for it)"
        )

    if question and question.strip():
        prompt = question.strip()

    else:
        prompt = "Analyze the storage usage and report what takes the most space."

    return f"User prompt:\n{prompt} \n\n Target path:\n{path}"


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
