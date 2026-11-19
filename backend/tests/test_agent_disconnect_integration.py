"""Real HTTP-disconnect regression test for MCP tool cancellation."""

import asyncio
import json
import re
import socket
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult

from storage_intelligence_backend.agents import storage_agent
from storage_intelligence_backend.main import create_app


class _FakeChatModel(GenericFakeChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
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


def _tool_call(name: str, args: dict[str, Any], call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _user_messages(text: str) -> list[dict[str, Any]]:
    return [{"id": "m1", "role": "user", "parts": [{"type": "text", "text": text}]}]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.integration
async def test_http_disconnect_cancels_real_mcp_worker(monkeypatch, capfd) -> None:
    path = str(Path(__file__).resolve().parents[2])
    model = _FakeChatModel(
        messages=iter(
            [
                _tool_call(
                    "find_duplicate_files",
                    {"path": path, "min_size_bytes": 1024},
                    "disconnect-cancel",
                ),
                AIMessage(content="never reached"),
            ]
        )
    )
    monkeypatch.setattr(storage_agent, "init_chat_model", lambda *args, **kwargs: model)

    app = create_app()
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    server_task = asyncio.create_task(server.serve())

    try:
        while not server.started:
            await asyncio.sleep(0.01)

        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            async with client.stream(
                "POST",
                "/api/agent/analyze",
                json={
                    "provider": "openai",
                    "model_name": "gpt-4.1",
                    "model": "openai-gpt-4.1",
                    "api_key": "test-key",
                    "path": path,
                    "messages": _user_messages("find duplicates"),
                },
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if "tool-input-available" in line:
                        await asyncio.sleep(1)
                        break
                await response.aclose()

        output = ""
        deadline = asyncio.get_running_loop().time() + 20
        while "cancel_requested=True" not in output:
            if asyncio.get_running_loop().time() >= deadline:
                break
            await asyncio.sleep(0.1)
            captured = capfd.readouterr()
            output += captured.out + captured.err

        assert "cancel_requested=True" in output
    finally:
        server.should_exit = True
        with suppress(asyncio.CancelledError):
            await server_task
