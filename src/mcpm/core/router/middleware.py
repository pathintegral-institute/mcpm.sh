import logging
from uuid import UUID

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from .extra import ClientMetaRequestProcessor, MetaRequestProcessor, ProfileMetaRequestProcessor
from .session import SessionManager

logger = logging.getLogger(__name__)

class SessionMiddleware:

    def __init__(
        self,
        app: ASGIApp,
        session_manager: SessionManager,
        meta_request_processors: list[MetaRequestProcessor] = [
            ProfileMetaRequestProcessor(),
            ClientMetaRequestProcessor(),
        ]
    ) -> None:
        self.app = app
        self.session_manager = session_manager
        # patch meta data from request to session
        self.meta_request_processors = meta_request_processors

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # we related metadata with session through this middleware, so that in the transport layer we only need to handle
        # session_id and dispatch message to the correct memory stream

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if scope["path"] == "/sse":
            # retrieve metadata from query params or header
            session = await self.session_manager.create_session()
            # session.meta will identically copied to JSONRPCMessage
            if self.meta_request_processors:
                for processor in self.meta_request_processors:
                    processor.process(request, session)

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
