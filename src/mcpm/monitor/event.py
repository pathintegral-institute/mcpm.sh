import datetime
import time
import typing
from functools import wraps

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    EmptyResult,
    GetPromptRequest,
    ReadResourceRequest,
    Request,
    ServerResult,
    TextContent,
)

from mcpm.core.router.router import PROMPT_SPLITOR, RESOURCE_SPLITOR, TOOL_SPLITOR

from .base import AccessEventType
from .duckdb import DuckDBAccessMonitor

monitor = DuckDBAccessMonitor()

RequestT = typing.TypeVar("RequestT", bound=Request)
MCPRequestHandler = typing.Callable[[RequestT], typing.Awaitable[ServerResult]]


class TraceIdentifier(typing.TypedDict):
    client_id: str
    server_id: str
    resource_id: str


class ResponseStatus(typing.TypedDict):
    success: bool
    error_message: str


def get_trace_identifier(req: Request) -> TraceIdentifier:
    resource_id = ""
    if isinstance(req, CallToolRequest):
        server_id = req.params.name.split(TOOL_SPLITOR, 1)[0]
    elif isinstance(req, GetPromptRequest):
        server_id = req.params.name.split(PROMPT_SPLITOR, 1)[0]
    elif isinstance(req, ReadResourceRequest):
        # resource uri is formatted as {server_id}:{protocol}://{resource_path}
        server_id, resource_id = str(req.params.uri).split(RESOURCE_SPLITOR, 1)
    else:
        # currently only support call tool, get prompt and read resource
        server_id = ""
        resource_id = ""

    return TraceIdentifier(client_id=req.params.meta.client_id, server_id=server_id, resource_id=resource_id)  # type: ignore


def get_response_status(server_result: ServerResult) -> ResponseStatus:
    result_root = server_result.root

    if isinstance(result_root, EmptyResult):
        return ResponseStatus(success=False, error_message="empty result")

    if isinstance(result_root, CallToolResult):
        if result_root.isError:
            return ResponseStatus(
                success=False,
                error_message=typing.cast(TextContent, result_root.content[0]).text,
            )
        else:
            return ResponseStatus(
                success=True,
                error_message="",
            )

    return ResponseStatus(success=True, error_message="")


def trace_event(event_type: AccessEventType):
    def decorator(func: MCPRequestHandler):
        @wraps(func)
        async def wrapper(request: Request):
            request_time = datetime.datetime.now().replace(microsecond=0)
            start_time = time.perf_counter()
            # parse client id, server id and resource id (optional) from request
            trace_identifier = get_trace_identifier(request)

            response: ServerResult = await func(request)

            # empty results and call tool failures are treated as not success
            response_status: ResponseStatus = get_response_status(response)

            await monitor.track_event(
                event_type=event_type,
                server_id=trace_identifier["server_id"],
                client_id=trace_identifier["client_id"],
                resource_id=trace_identifier["resource_id"],
                timestamp=request_time,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
                request_size=len(request.params.model_dump_json().encode("utf-8")),
                response_size=len(response.root.model_dump_json().encode("utf-8")),
                success=response_status["success"],
                error_message=response_status["error_message"],
                metadata=None,
                raw_request=request.model_dump_json(),
                raw_response=response.root.model_dump_json(),
            )
            return response

        return wrapper

    return decorator
