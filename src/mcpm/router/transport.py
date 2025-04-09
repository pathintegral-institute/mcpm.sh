import json
import logging
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import types
from mcp.server.sse import SseServerTransport
from pydantic import ValidationError
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

logger = logging.getLogger(__name__)


def patch_meta_data(body: bytes, profile: str) -> bytes:
    data = json.loads(body.decode("utf-8"))
    if "params" not in data:
        data["params"] = {}

    if "_meta" not in data["params"]:
        data["params"]["_meta"] = {}

    data["params"]["_meta"]["profile"] = profile
    return json.dumps(data).encode("utf-8")


def _get_query_key_from_scope(scope: Scope, key_name: str) -> str | None:
    logger.info(f"Scope: {scope}")
    query_string = scope.get("query_string", b"")

    query_str = query_string.decode("utf-8")

    params = {}
    if query_str:
        param_pairs = query_str.split("&")
        for pair in param_pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value

    if key_name in params:
        return params[key_name]

    # if can't find in query string, fallback to headers
    headers = scope.get("headers", [])
    for header_name, header_value in headers:
        if header_name.decode("utf-8").lower() == key_name.lower():
            return header_value.decode("utf-8")

    return None


class RouterSseTransport(SseServerTransport):
    """A SSE server transport that is used by the router to handle client connections."""

    def __init__(self, *args, **kwargs):
        self._session_id_to_profile: dict[UUID, str] = {}
        super().__init__(*args, **kwargs)

    @asynccontextmanager
    async def connect_sse(self, scope: Scope, receive: Receive, send: Send):
        # almost the same as parent class, but add a session_id to profile mapping
        if scope["type"] != "http":
            logger.error("connect_sse received non-HTTP request")
            raise ValueError("connect_sse can only handle HTTP requests")

        logger.debug("Setting up SSE connection")
        read_stream: MemoryObjectReceiveStream[types.JSONRPCMessage | Exception]
        read_stream_writer: MemoryObjectSendStream[types.JSONRPCMessage | Exception]

        write_stream: MemoryObjectSendStream[types.JSONRPCMessage]
        write_stream_reader: MemoryObjectReceiveStream[types.JSONRPCMessage]

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        session_id = uuid4()
        session_uri = f"{quote(self._endpoint)}?session_id={session_id.hex}"
        self._read_stream_writers[session_id] = read_stream_writer
        logger.debug(f"Created new session with ID: {session_id}")
        # maintain session_id to profile mapping
        profile = _get_query_key_from_scope(scope, key_name="profile")
        if profile is not None:
            self._session_id_to_profile[session_id] = profile
            logger.info(f"Session {session_id} mapped to profile {profile}")

        sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[dict[str, Any]](0)

        async def sse_writer():
            logger.debug("Starting SSE writer")
            async with sse_stream_writer, write_stream_reader:
                await sse_stream_writer.send({"event": "endpoint", "data": session_uri})
                logger.debug(f"Sent endpoint event: {session_uri}")

                async for message in write_stream_reader:
                    logger.debug(f"Sending message via SSE: {message}")
                    await sse_stream_writer.send(
                        {
                            "event": "message",
                            "data": message.model_dump_json(by_alias=True, exclude_none=True),
                        }
                    )

        async with anyio.create_task_group() as tg:
            response = EventSourceResponse(content=sse_stream_reader, data_sender_callable=sse_writer)
            logger.debug("Starting SSE response task")
            tg.start_soon(response, scope, receive, send)

            logger.debug("Yielding read and write streams")
            yield (read_stream, write_stream)

    async def handle_post_message(self, scope: Scope, receive: Receive, send: Send):
        logger.debug("Handling POST message")
        request = Request(scope, receive)

        session_id_param = request.query_params.get("session_id")
        if session_id_param is None:
            logger.warning("Received request without session_id")
            response = Response("session_id is required", status_code=400)
            return await response(scope, receive, send)

        try:
            session_id = UUID(hex=session_id_param)
            logger.info(f"Parsed session ID: {session_id}")
        except ValueError:
            logger.warning(f"Received invalid session ID: {session_id_param}")
            response = Response("Invalid session ID", status_code=400)
            return await response(scope, receive, send)

        writer = self._read_stream_writers.get(session_id)
        if not writer:
            logger.warning(f"Could not find session for ID: {session_id}")
            response = Response("Could not find session", status_code=404)
            return await response(scope, receive, send)

        body = await request.body()
        logger.info(f"Received JSON: {body}")

        # find profile through session_id
        profile = self._session_id_to_profile.get(session_id)
        if not profile:
            logger.warning(f"Could not find profile for session ID: {session_id}")
            response = Response("Could not find profile", status_code=404)
            return await response(scope, receive, send)

        # append profile to params metadata so that the downstream mcp server could attach
        body = patch_meta_data(body, profile)

        try:
            message = types.JSONRPCMessage.model_validate_json(body)
            logger.info(f"Validated client message: {message}")
        except ValidationError as err:
            logger.error(f"Failed to parse message: {err}")
            response = Response("Could not parse message", status_code=400)
            await response(scope, receive, send)
            await writer.send(err)
            return

        logger.info(f"Sending message to writer: {message}")
        response = Response("Accepted", status_code=202)
        await response(scope, receive, send)
        await writer.send(message)
