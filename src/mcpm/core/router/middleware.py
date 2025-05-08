import logging
from typing import Any
from uuid import UUID

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .session import SessionManager

logger = logging.getLogger(__name__)

META_DATA_KEYS = ["profile", "client"]

def get_meta(request: Request) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for key in META_DATA_KEYS:
        value = request.query_params.get(key)
        if not value:
            value = request.headers.get(key)

        if value:
            meta[key] = value
            if key == "client":
                # legacy client id
                meta["client_id"] = value

    if "client_id" not in meta:
        meta["client_id"] = "anonymous"

    return meta

class SessionMiddleware:

    def __init__(self, app: ASGIApp, session_manager: SessionManager) -> None:
        self.app = app
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # we related metadata with session through this middleware, so that in the transport layer we only need to handle
        # session_id and dispatch message to the correct memory stream

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if scope["path"] == "/sse":
            # retrieve metadata from query params or header
            session = await self.session_manager.create_session(meta=get_meta(request))
            logger.debug(f"Created new session with ID: {session['id']}")

            scope["session_id"] = session["id"].hex

        if scope["path"] == "/messages/":
            session_id_param = request.query_params.get("session_id")
            if not session_id_param:
                logger.debug("Missing session_id")
                response = Response("session_id is required", status_code=400)
                await response(scope, receive, send)
                return

            # validate session_id
            try:
                session_id = UUID(hex=session_id_param)
            except ValueError:
                logger.warning(f"Received invalid session ID: {session_id_param}")
                response = Response("invalid session ID", status_code=400)
                await response(scope, receive, send)
                return

            # if session_id is not in session manager, return 404
            if not self.session_manager.exist(session_id):
                logger.debug(f"session {session_id} not found")
                response = Response("session not found", status_code=404)
                await response(scope, receive, send)
                return

            scope["session_id"] = session_id.hex

        await self.app(scope, receive, send)
