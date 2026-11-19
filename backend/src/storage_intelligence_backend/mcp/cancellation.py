"""Request-ID tracking for cancelling in-flight MCP tool calls."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager, suppress
from contextvars import ContextVar, Token
from dataclasses import dataclass, field, replace
from typing import Any, cast

from fastmcp import Client
from fastmcp.client.transports import UvStdioTransport
from fastmcp.client.transports.base import TransportOptions
from mcp import ClientSession
from mcp.shared.dispatcher import CallOptions
from mcp.shared.jsonrpc_dispatcher import JSONRPCDispatcher
from mcp.types import RequestId

_current_run_id: ContextVar[str | None] = ContextVar("mcp_run_id", default=None)


@dataclass
class ToolRequestTracker:
    """Active MCP request IDs grouped by the agent run that issued them."""

    _requests: dict[str, dict[RequestId, bool]] = field(default_factory=dict)

    def track(self, run_id: str, request_id: RequestId) -> None:
        self._requests.setdefault(run_id, {})[request_id] = True

    def complete(self, run_id: str, request_id: RequestId) -> None:
        requests = self._requests.get(run_id)
        if requests is not None and request_id in requests:
            requests[request_id] = False

    def pop_active(self, run_id: str) -> list[RequestId]:
        requests = self._requests.pop(run_id, {})
        return [request_id for request_id, active in requests.items() if active]


tool_request_tracker = ToolRequestTracker()


def set_current_run_id(run_id: str) -> Token[str | None]:
    return _current_run_id.set(run_id)


def reset_current_run_id(token: Token[str | None]) -> None:
    _current_run_id.reset(token)


class ToolRequestDispatcher(JSONRPCDispatcher):
    """Record tool-call request IDs while leaving JSON-RPC to the SDK."""

    async def send_raw_request(
        self,
        method: str,
        params: Mapping[str, Any] | None,
        opts: CallOptions | None = None,
        *,
        _related_request_id: RequestId | None = None,
    ) -> dict[str, Any]:
        options = cast(CallOptions, dict(opts or {}))
        request_id = options.get("request_id")
        if request_id is None:
            request_id = str(uuid.uuid4())
            options["request_id"] = request_id

        run_id = _current_run_id.get()
        tracked = method == "tools/call" and run_id is not None
        if tracked and run_id is not None:
            tool_request_tracker.track(run_id, request_id)

        try:
            result = await super().send_raw_request(
                method, params, options, _related_request_id=_related_request_id
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            if tracked and run_id is not None:
                tool_request_tracker.complete(run_id, request_id)
            raise
        else:
            if tracked and run_id is not None:
                tool_request_tracker.complete(run_id, request_id)
            return result


class TrackingClientSession(ClientSession):
    def __init__(self, read_stream: Any, write_stream: Any, **kwargs: Any) -> None:
        super().__init__(dispatcher=ToolRequestDispatcher(read_stream, write_stream), **kwargs)


class TrackingUvStdioTransport(UvStdioTransport):
    # pyrefly: ignore[deprecated]
    @asynccontextmanager
    async def connect_session(
        self,
        *,
        transport_options: TransportOptions | None = None,
        **session_kwargs: Any,
    ) -> AsyncIterator[ClientSession]:
        options = replace(
            transport_options or TransportOptions(),
            session_class=TrackingClientSession,
        )
        async with super().connect_session(
            transport_options=options, **session_kwargs
        ) as session:
            yield session


async def cancel_active_requests(client: Client, reason: str) -> None:
    run_id = _current_run_id.get()
    if run_id is None:
        return

    for request_id in tool_request_tracker.pop_active(run_id):
        asyncio.create_task(_cancel_request(client, request_id, reason))


async def _cancel_request(client: Client, request_id: RequestId, reason: str) -> None:
    with suppress(Exception, asyncio.CancelledError):
        await client.cancel(request_id, reason)
