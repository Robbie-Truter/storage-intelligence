"""Read-only LangChain agent over an explicit allowlist of MCP tools.

The tool catalogue comes from the manager, which hands over only the tools in
``READONLY_TOOL_ALLOWLIST`` (including the MCP server's ``preview_trash``
tool); the raw ``trash_path`` tool is never among them. The allowlist is the
manager's business - see ``StorageMCPClient.langchain_tools``.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from storage_intelligence_backend.agents.errors import AgentModelError, format_model_error
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


async def stream_readonly_analysis(
    agent: Any,
    path: str | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream agent events for ``path`` as dicts ready for SSE framing.

    Yields ``{"type": "tool_call", ...}`` events as the agent invokes tools,
    ``{"type": "text_delta", "content": "..."}`` as the model writes its reply,
    and a final ``{"type": "complete", "summary": "...", "tool_calls": [...]}``
    when the run finishes.

    Errors from the model provider are translated to ``AgentModelError``;
    MCP transport failures become ``MCPUnavailable``; a step-cap breach
    propagates as ``GraphRecursionError``.

    Raises:
        MCPUnavailable: The MCP server connection broke during the run.
        AgentModelError: The AI model or provider failed or is overloaded.
        GraphRecursionError: The agent exceeded its step limit.
    """

    conversation = _convert_messages(messages or [])

    # Format the latest user message with the existing prompt builder.
    if conversation and isinstance(conversation[-1], HumanMessage):
        latest_message = conversation[-1]
        latest_message.content = _build_prompt(
            path=path,
            question=_content_text(latest_message.content),
        )

    elif not conversation:
        conversation = [HumanMessage(content=_build_prompt(path=path))]

    # astream_events is an async generator - do NOT await it.
    seen_tool_ids: set[str] = set()
    all_messages: list[Any] = []

    # Hold a reference so we can call aclose() in the finally block.
    # This is critical for cancellation: if the caller task is cancelled,
    # the finally block fires aclose() which propagates GeneratorExit into
    # LangGraph's Pregel loop and signals its internal task groups to stop.
    # Without this, LangGraph's in-flight tool call tasks become orphaned
    # and keep running even after the HTTP client has disconnected.
    stream = agent.astream_events(
        {"messages": conversation},
        version="v2",
    )
    try:
        async for event in stream:
            kind: str = event["event"]

            # --- Incremental text from the final answer ---
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk is not None:
                    text = chunk.text
                    if text:
                        yield {"type": "text_delta", "content": text}

            # --- Tool invocations ---
            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                run_id = event.get("run_id", "")
                if run_id and run_id not in seen_tool_ids:
                    seen_tool_ids.add(run_id)
                    yield {
                        "id": run_id,
                        "type": "tool_call",
                        "name": tool_name,
                        "args": event["data"].get("input") or {},
                    }

            elif kind == "on_tool_end":
                run_id = event.get("run_id", "")
                output = event["data"].get("output") or {}

                yield {
                    "type": "tool_result",
                    "id": run_id,
                    "result": output.content if isinstance(output, ToolMessage) else output,
                }

            # --- Final graph output: collect all messages for the summary ---
            elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                output = event["data"].get("output") or {}
                all_messages = output.get("messages", [])

    except asyncio.CancelledError:
        raise
    except (MCPError, GraphRecursionError):
        raise
    except ConnectionError as exc:
        raise MCPUnavailable(f"Agent run failed: {exc}") from exc
    except Exception as exc:
        status_code, clean_message = format_model_error(exc)
        raise AgentModelError(clean_message, status_code=status_code) from exc
    finally:
        # aclose() on an already-exhausted generator is a no-op, so this is
        # always safe. On cancellation it is essential: it sends GeneratorExit
        # into LangGraph's Pregel runner, which cancels its internal asyncio
        # task groups (including any in-flight MCP tool call task).
        await stream.aclose()

    yield {
        "type": "complete",
        "summary": _final_summary(all_messages),
        "tool_calls": _tool_call_records(all_messages),
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


def _convert_messages(messages: list[dict[str, Any]]) -> list[Any]:
    """Convert Vercel AI SDK UIMessage objects into LangChain messages.

    Only completed user-assistant pairs are preserved in conversation history,
    plus the final active user message.

    If a previous user request was cancelled or aborted before the assistant
    could produce a response, that unfulfilled user request is omitted from the
    history. Otherwise, the agent would see multiple pending user prompts and
    attempt to answer the cancelled question (re-invoking its tools) alongside
    the new question.
    """
    raw_turns: list[tuple[str, str]] = []
    for message in messages:
        role = message.get("role")
        if role not in ("user", "assistant"):
            continue
        parts = message.get("parts", [])
        content = "\n".join(
            part["text"] for part in parts if part.get("type") == "text" and part.get("text")
        ).strip()
        if content:
            raw_turns.append((role, content))

    history_turns: list[tuple[str, str]] = []
    current_user_turn: tuple[str, str] | None = None

    if raw_turns and raw_turns[-1][0] == "user":
        current_user_turn = raw_turns[-1]
        prior_turns = raw_turns[:-1]
    else:
        prior_turns = raw_turns

    i = 0
    while i < len(prior_turns):
        role, _ = prior_turns[i]
        if role == "user":
            if i + 1 < len(prior_turns) and prior_turns[i + 1][0] == "assistant":
                history_turns.append(prior_turns[i])
                history_turns.append(prior_turns[i + 1])
                i += 2
            else:
                # User message with no assistant response (cancelled/aborted) -> drop it.
                i += 1
        elif role == "assistant":
            history_turns.append(prior_turns[i])
            i += 1

    if current_user_turn:
        history_turns.append(current_user_turn)

    converted: list[Any] = []
    for role, content in history_turns:
        if role == "user":
            converted.append(HumanMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))

    return converted
