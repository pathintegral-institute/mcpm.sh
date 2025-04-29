import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote
from uuid import UUID

import anyio
from mcp import types
from pydantic import ValidationError
from sse_starlette import EventSourceResponse
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from .session import Session, SessionManager

logger = logging.getLogger(__name__)

def patch_meta_data(body: bytes, **kwargs) -> bytes:
    data = json.loads(body.decode("utf-8"))
    if "params" not in data:
        data["params"] = {}

    for key, value in kwargs.items():
        data["params"].setdefault("_meta", {})[key] = value
    return json.dumps(data).encode("utf-8")

class SseTransport:

    def __init__(self, endpoint: str, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self._endpoint = endpoint

    @asynccontextmanager
    async def connect_sse(self, scope: Scope, receive: Receive, send: Send):
        session_id_hex = scope["session_id"]
        session_id: UUID = UUID(hex=session_id_hex)
        session = await self.session_manager.get_session(session_id)

        session_uri = f"{quote(self._endpoint)}?session_id={session_id.hex}"

        sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[dict[str, Any]](0)

        async def sse_writer():
            logger.debug("Starting SSE writer")
            async with sse_stream_writer, session["write_stream_reader"]:
                await sse_stream_writer.send({"event": "endpoint", "data": session_uri})
                logger.debug(f"Sent endpoint event: {session_uri}")

                async for message in session["write_stream_reader"]:
                    logger.debug(f"Sending message via SSE: {message}")
                    await sse_stream_writer.send(
                        {
                            "event": "message",
                            "data": message.model_dump_json(by_alias=True, exclude_none=True),
                        }
                    )

        async with anyio.create_task_group() as tg:
            async def on_client_disconnect():
                await self.session_manager.close_session(session_id)

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
                yield (session["read_stream"], session["write_stream"])
            except asyncio.CancelledError as exc:
                logger.warning(f"SSE connection for session {session_id} was cancelled")
                tg.cancel_scope.cancel()
                # raise the exception again so that to interrupt mcp server run operation
                raise exc
            finally:
                # for server shutdown
                await self.session_manager.cleanup_resources()

    async def handle_post_message(self, scope: Scope, receive: Receive, send: Send):

        session_id = scope["session_id"]
        session: Session = await self.session_manager.get_session(UUID(hex=session_id))

        request = Request(scope, receive)
        body = await request.body()
        # patch meta data
        body = patch_meta_data(body, **session["meta"])

        # send message to writer
        writer = session["read_stream_writer"]
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

        logger.debug(f"Sending message to writer: {message}")
        response = Response("Accepted", status_code=202)
        await response(scope, receive, send)

        # add error handling, catch possible pipe errors
        try:
            await writer.send(message)
        except (BrokenPipeError, ConnectionError, OSError) as e:
            # if it's EPIPE error or other connection error, log it but don't throw an exception
            if isinstance(e, OSError) and e.errno == 32:  # EPIPE
                logger.warning(f"EPIPE error when sending message to session {session_id}, connection may be closing")
            else:
                logger.warning(f"Connection error when sending message to session {session_id}: {e}")
                await self.session_manager.close_session(session_id)
