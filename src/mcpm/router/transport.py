import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, TypedDict
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid4

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from deprecated import deprecated
from mcp import types
from mcp.server.sse import SseServerTransport
from mcp.shared.message import SessionMessage
from pydantic import ValidationError
from sse_starlette import EventSourceResponse
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from mcpm.utils.config import ConfigManager

logger = logging.getLogger(__name__)


class ClientIdentifier(TypedDict):
    client_id: str
    profile: str
    api_key: str | None


def patch_meta_data(body: bytes, **kwargs) -> bytes:
    data = json.loads(body.decode("utf-8"))
    if "params" not in data:
        data["params"] = {}

    for key, value in kwargs.items():
        data["params"].setdefault("_meta", {})[key] = value
    return json.dumps(data).encode("utf-8")


def get_key_from_scope(scope: Scope, key_name: str) -> str | None:
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


@deprecated
class RouterSseTransport(SseServerTransport):
    """A SSE server transport that is used by the router to handle client connections."""

    def __init__(self, *args, api_key: str | None = None, **kwargs):
        self._session_id_to_identifier: dict[UUID, ClientIdentifier] = {}
        self.api_key = api_key
        super().__init__(*args, **kwargs)

    @asynccontextmanager
    async def connect_sse(self, scope: Scope, receive: Receive, send: Send):
        # almost the same as parent class, but add a session_id to profile mapping
        if scope["type"] != "http":
            logger.error("connect_sse received non-HTTP request")
            raise ValueError("connect_sse can only handle HTTP requests")

        # check api key
        api_key = get_key_from_scope(scope, key_name="s")
        if not self._validate_api_key(scope, api_key):
            response = Response("Unauthorized API key", status_code=401)
            await response(scope, receive, send)
            return

        logger.debug("Setting up SSE connection")
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
        read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]

        write_stream: MemoryObjectSendStream[SessionMessage]
        write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        session_id = uuid4()
        session_uri = f"{quote(self._endpoint)}?session_id={session_id.hex}"
        self._read_stream_writers[session_id] = read_stream_writer
        logger.debug(f"Created new session with ID: {session_id}")
        # maintain session_id to identifier mapping
        profile = get_key_from_scope(scope, key_name="profile")
        client_id = get_key_from_scope(scope, key_name="client")
        logger.debug(f"Profile: {profile}, Client ID: {client_id}")
        client_id = client_id or "anonymous"
        profile = profile or "default"
        self._session_id_to_identifier[session_id] = ClientIdentifier(
            client_id=client_id, profile=profile, api_key=api_key
        )
        logger.debug(f"Session {session_id} mapped to identifier {self._session_id_to_identifier[session_id]}")

        sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[dict[str, Any]](0)

        async def sse_writer():
            logger.debug("Starting SSE writer")
            async with sse_stream_writer, write_stream_reader:
                await sse_stream_writer.send({"event": "endpoint", "data": session_uri})
                logger.debug(f"Sent endpoint event: {session_uri}")

                async for session_message in write_stream_reader:
                    logger.debug(f"Sending message via SSE: {session_message}")
                    await sse_stream_writer.send(
                        {
                            "event": "message",
                            "data": session_message.message.model_dump_json(by_alias=True, exclude_none=True),
                        }
                    )

        async def cleanup_resources(session_id: UUID):
            if session_id in self._read_stream_writers:
                self._read_stream_writers.pop(session_id, None)
                self._session_id_to_identifier.pop(session_id, None)
                logger.debug(f"Session {session_id} cleaned")

        async with anyio.create_task_group() as tg:

            async def on_client_disconnect():
                # for client disconnection, but still we can't close transport cause there's no
                # method to interrupt mcp server run operation
                logger.debug(f"Client disconnected from session {session_id}")
                await cleanup_resources(session_id)
                await read_stream_writer.aclose()
                await write_stream.aclose()

            try:
                response = EventSourceResponse(
                    content=sse_stream_reader,
                    data_sender_callable=sse_writer,
                    background=BackgroundTask(on_client_disconnect),
                )
                logger.debug("Starting SSE response task")
                tg.start_soon(response, scope, receive, send)

                logger.debug("Yielding read and write streams")
                # Due to limitations with interrupting the MCP server run operation,
                # this will always block here regardless of client disconnection status
                yield (read_stream, write_stream)
            except asyncio.CancelledError as exc:
                logger.warning(f"SSE connection for session {session_id} was cancelled")
                tg.cancel_scope.cancel()
                # raise the exception again so that to interrupt mcp server run operation
                raise exc
            finally:
                # for server shutdown
                await cleanup_resources(session_id)

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
            logger.debug(f"Parsed session ID: {session_id}")
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
        logger.debug(f"Received JSON: {body}")

        # find profile through session_id
        identifier = self._session_id_to_identifier.get(session_id)
        if not identifier:
            logger.warning(f"Could not find identifier for session ID: {session_id}")
            response = Response("Could not find identifier", status_code=404)
            return await response(scope, receive, send)

        # check api key
        api_key = identifier["api_key"]
        if not self._validate_api_key(scope, api_key):
            response = Response("Unauthorized API key", status_code=401)
            await response(scope, receive, send)
            return

        # append profile to params metadata so that the downstream mcp server could attach
        body = patch_meta_data(body, profile=identifier["profile"], client_id=identifier["client_id"], api_key=api_key)

        try:
            message = types.JSONRPCMessage.model_validate_json(body)
            logger.debug(f"Validated client message: {message}")
        except ValidationError as err:
            logger.error(f"Failed to parse message: {err}")
            response = Response("Could not parse message", status_code=400)
            await response(scope, receive, send)
            try:
                await writer.send(err)
            except (BrokenPipeError, ConnectionError, OSError) as pipe_err:
                logger.warning(f"Failed to send error due to pipe issue: {pipe_err}")
            return

        # Send the 202 Accepted response
        accepted_response = Response("Accepted", status_code=202)
        await accepted_response(scope, receive, send)

        # Attempt to send the message to the writer
        try:
            await writer.send(SessionMessage(message=message))
        except (BrokenPipeError, ConnectionError, OSError) as e:
            # if it's EPIPE error or other connection error, log it but don't throw an exception
            if isinstance(e, OSError) and e.errno == 32:  # EPIPE
                logger.warning(f"EPIPE error when sending message to session {session_id}, connection may be closing")
            else:
                logger.warning(f"Connection error when sending message to session {session_id}: {e}")
                self._read_stream_writers.pop(session_id, None)
                self._session_id_to_identifier.pop(session_id, None)

        # Implicitly return None. The original 'return response' is removed.
        return

    def _validate_api_key(self, scope: Scope, api_key: str | None) -> bool:
        # If api_key is explicitly set to None, disable API key validation
        if self.api_key is None:
            logger.debug("API key validation disabled")
            return True

        # If we have a directly provided API key, verify it matches
        if api_key == self.api_key:
            return True

        # At this point, self.api_key is not None but doesn't match the provided api_key
        # Let's check if this is a share URL that needs special validation
        try:
            config_manager = ConfigManager()
            host = get_key_from_scope(scope, key_name="host") or ""
            if not host.startswith("http"):
                host = f"http://{host}"
            router_config = config_manager.get_router_config()
            host_name = urlsplit(host).hostname
            if host_name != router_config["host"]:
                if api_key != self.api_key:
                    return False
        except Exception as e:
            logger.error(f"Failed to validate API key: {e}")
            return False

        return True
