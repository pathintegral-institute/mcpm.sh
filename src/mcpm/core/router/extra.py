
from typing import Any, Protocol

from mcp.types import ServerResult
from starlette.requests import Request

from mcpm.core.router.session import Session


class MetaRequestProcessor(Protocol):

    def process(self, request: Request, session: Session):
        ...

class MetaResponseProcessor(Protocol):

    def process(self, response: ServerResult, request_context: dict[str, Any], response_context: dict[str, Any]) -> ServerResult:
        ...

class ProfileMetaRequestProcessor:

    def process(self, request: Request, session: Session):
        profile = request.query_params.get("profile")
        if not profile:
            # fallback to headers
            profile = request.headers.get("profile")

        if profile:
            session["meta"]["profile"] = profile

class ClientMetaRequestProcessor:

    def process(self, request: Request, session: Session):
        client = request.query_params.get("client")
        if client:
            session["meta"]["client_id"] = client


class MCPResponseProcessor:

    def process(self, response: ServerResult, request_context: dict[str, Any], response_context: dict[str, Any]) -> ServerResult:
        if not response.root.meta:
            response.root.meta = {}

        response.root.meta.update({
            "request_context": request_context,
            "response_context": response_context,
        })
        return response
