# FastMCP Progress Notification Investigation

**Date**: July 8, 2025  
**Issue**: Progress notifications not working when FastMCP proxy uses HTTP-to-Stdio transport  
**Status**: Root cause identified, architectural limitation in FastMCP  

## Executive Summary

Progress notifications work correctly when FastMCP proxy communicates with servers via HTTP-to-HTTP transport, but fail when using HTTP-to-Stdio transport. The issue is a context isolation problem in FastMCP's proxy implementation where progress tokens cannot be properly tracked across process boundaries.

## Issue Description

### Observed Behavior

When running a server through MCPM's FastMCP proxy:

**Working Case (HTTP → Proxy → HTTP):**
- Progress notifications flow correctly from server to client
- Progress tokens are preserved throughout the request lifecycle

**Failing Case (HTTP → Proxy → Stdio):**
- Progress notifications are received by proxy but fail to forward to client
- Error: `[CONTEXT] No progress token available, skipping notification`

### Error Logs

```
2025-07-08 20:22:36,003 - timer.main - DEBUG - Sending progress notification: 10000/180000 ms
[07/08/25 20:22:36] INFO     FastMCP.fastmcp.server.proxy: received progress notification: progress=10000.0, total=180000.0, message=None                                                                                                                                                               
                    DEBUG    fastmcp.server.context: [CONTEXT] Reporting progress: progress=10000.0, total=180000.0, message=None                                                                                                                                                                       
                    DEBUG    fastmcp.server.context: [CONTEXT] No progress token available, skipping notification   
```

## Technical Root Cause Analysis

### MCP Protocol Support

The MCP protocol **correctly supports** progress notifications across all transports:

1. **Progress Token Propagation**: MCP passes progress tokens in `_meta.progressToken` field
2. **Request Metadata**: Found in `/mcp/types.py:43-50`:
   ```python
   class RequestParams(BaseModel):
       class Meta(BaseModel):
           progressToken: ProgressToken | None = None
           """
           If specified, the caller requests out-of-band progress notifications for
           this request (as represented by notifications/progress). The value of this
           parameter is an opaque token that will be attached to any subsequent
           notifications.
           """
   ```

3. **Session Implementation**: In `/mcp/shared/session.py:443+`, `send_request` properly sets progress tokens:
   ```python
   # Set up progress token if progress callback is provided
   if progress_callback is not None:
       # Use request_id as progress token
       if "_meta" not in request_data["params"]:
           request_data["params"]["_meta"] = {}
       request_data["params"]["_meta"]["progressToken"] = request_id
       # Store the callback for this request
       self._progress_callbacks[request_id] = progress_callback
   ```

### FastMCP Implementation Details

**Progress Handler Location**: `/fastmcp/server/proxy.py:514-539`
```python
@classmethod
async def default_progress_handler(
    cls,
    progress: float,
    total: float | None,
    message: str | None,
) -> None:
    """
    A handler that forwards the progress notification from the remote server to the proxy's connected clients.
    """
    ctx = get_context()
    logger.info("received progress notification: progress=%s, total=%s, message=%s", progress, total, message)
    await ctx.report_progress(progress, total, message)
```

**Context Report Progress**: `/fastmcp/server/context.py:125-155`
```python
async def report_progress(
    self, progress: float, total: float | None = None, message: str | None = None
) -> None:
    progress_token = (
        self.request_context.meta.progressToken
        if self.request_context.meta
        else None
    )

    if progress_token is None:
        logger.debug("[CONTEXT] No progress token available, skipping notification")
        return

    await self.session.send_progress_notification(
        progress_token=progress_token,
        progress=progress,
        total=total,
        message=message,
        related_request_id=self.request_id,
    )
```

### Context Isolation Problem

**HTTP-to-HTTP Flow (✅ Working):**
```
Client Request (HTTP) → Proxy → HTTP Server
├─ Request context with progressToken flows through HTTP session
├─ Progress handler executes in same HTTP context
└─ Progress notifications reference original progressToken
```

**HTTP-to-Stdio Flow (❌ Broken):**
```
Client Request (HTTP) → Proxy → Stdio Subprocess
├─ Request context with progressToken sent to subprocess
├─ Subprocess runs in isolated process with separate context
├─ Progress handler (`default_progress_handler`) runs in subprocess context
├─ `get_context()` returns subprocess context (no original progressToken)
└─ Progress notification dropped due to missing token
```

### Key Technical Components

1. **Context Management**: `/fastmcp/server/dependencies.py:27-33`
   ```python
   def get_context() -> Context:
       from fastmcp.server.context import _current_context
       context = _current_context.get()
       if context is None:
           raise RuntimeError("No active context found.")
       return context
   ```

2. **Context Variables**: Uses Python `ContextVar` which is isolated per async task/process

3. **Stdio Transport**: `/fastmcp/client/transports.py:300+` - Creates subprocess with separate memory space

## Debug Implementation Added

### Debug Middleware

Created `MCPMDebugMiddleware` in `/src/mcpm/fastmcp_integration/middleware.py:19-198`:

- **Limitation Documented**: Middleware only intercepts messages flowing FROM clients TO servers
- **Progress notifications flow FROM servers TO clients**, bypassing middleware pipeline
- **Added debug flags** to `mcpm run --debug` and `mcpm profile run --debug`

### Enhanced Logging

Added debug logging in multiple layers:

1. **Proxy Progress Handler**: `/fastmcp/server/proxy.py:524+`
2. **Context Report Progress**: `/fastmcp/server/context.py:134-147`
3. **Debug context inspection** in progress handler

## Architectural Limitation

### Why This Is Hard to Fix

FastMCP's proxy architecture has a fundamental limitation:

1. **Process Isolation**: Stdio servers run in separate processes with isolated memory
2. **Context Variables**: `_current_context` is per-process, not shared
3. **Missing Mapping**: No mechanism to associate stdio server progress with original client requests

### Required Fix

To properly support HTTP-to-Stdio progress notifications, FastMCP would need:

1. **Request Tracking**: Maintain mapping between client requests and stdio subprocess instances
2. **Token Preservation**: Store original progress tokens when spawning stdio requests  
3. **Context Injection**: Inject correct progress token when handling progress from stdio servers

Example fix architecture:
```python
class ProxyRequestTracker:
    def __init__(self):
        self._request_mapping: Dict[subprocess_id, ProgressToken] = {}
    
    def track_request(self, subprocess_id: str, progress_token: ProgressToken):
        self._request_mapping[subprocess_id] = progress_token
    
    def get_progress_token(self, subprocess_id: str) -> ProgressToken | None:
        return self._request_mapping.get(subprocess_id)
```

## Current Workarounds

### For Users

1. **Use HTTP servers** when progress notifications are needed:
   ```bash
   mcpm run server-name --http --port 8001
   ```

2. **Debug with HTTP-to-HTTP** setup:
   ```bash
   mcpm run timer --http --debug
   ```

### For Development

1. **Enable comprehensive debug logging**:
   ```bash
   export PYTHONUNBUFFERED=1
   export LOG_LEVEL=DEBUG
   mcpm run server-name --debug
   ```

2. **Use enhanced logging** in FastMCP components (already added)

## Files Modified During Investigation

### MCPM Code Changes

1. **Debug Middleware**: `/src/mcpm/fastmcp_integration/middleware.py`
   - Added `MCPMDebugMiddleware` class with comprehensive logging
   - Handles all MCP operations: tools, resources, prompts, notifications
   - Safe serialization for complex objects

2. **Proxy Factory**: `/src/mcpm/fastmcp_integration/proxy.py`
   - Added `debug: bool` parameter to `MCPMProxyFactory`
   - Debug middleware added first in middleware chain when enabled
   - Updated convenience function `create_mcpm_proxy()`

3. **CLI Commands**:
   - `/src/mcpm/commands/run.py`: Added `--debug` flag
   - `/src/mcpm/commands/profile/run.py`: Added `--debug` flag
   - Debug parameter propagated through all execution paths

### FastMCP Library Changes (for debugging)

1. **Proxy Progress Handler**: `/fastmcp/server/proxy.py:524`
   - Fixed logging syntax error (string formatting)
   - Added comprehensive debug context inspection

2. **Context Report Progress**: `/fastmcp/server/context.py:134-147`
   - Added detailed debug logging for progress reporting
   - Logs progress token availability and notification sending

## Testing and Validation

### Confirmed Working Cases

- **HTTP-to-HTTP**: Progress notifications work correctly
- **Local servers**: Progress works when not proxied
- **Debug logging**: All layers now provide detailed debugging information

### Confirmed Failing Cases

- **HTTP-to-Stdio**: Progress notifications fail due to context isolation
- **Any proxied stdio server**: Same issue across all stdio transport types

### Debug Output Examples

**Working HTTP-to-HTTP**:
```
[PROXY DEBUG] TOOL CALL: timer_tool
[CONTEXT] Reporting progress: progress=10000.0, total=180000.0, message=None
[CONTEXT] Sending progress notification with token=12345
```

**Failing HTTP-to-Stdio**:
```
[PROXY DEBUG] TOOL CALL: timer_tool  
INFO: received progress notification: progress=10000.0, total=180000.0, message=None
[CONTEXT] Reporting progress: progress=10000.0, total=180000.0, message=None
[CONTEXT] No progress token available, skipping notification
```

## Future Work Recommendations

### FastMCP Core Fix

The proper solution requires changes to FastMCP core:

1. **Enhance ProxyClient**: Maintain request-to-subprocess mapping
2. **Modify default_progress_handler**: Inject correct progress token from mapping
3. **Add request lifecycle tracking**: Clean up mappings when requests complete

### Alternative Approaches

1. **HTTP Wrapper Pattern**: Create HTTP servers that wrap stdio servers
2. **Progress Relay Service**: Separate service to bridge context gaps
3. **Enhanced Middleware**: Middleware that can intercept outgoing notifications

### Testing Strategy

1. **Unit tests** for request tracking components
2. **Integration tests** for HTTP-to-Stdio progress scenarios  
3. **Performance testing** for overhead of request tracking

## References

### Key Files Investigated

- `/mcp/types.py`: MCP protocol definitions including progress tokens
- `/mcp/shared/session.py`: Base session with progress token handling
- `/mcp/client/session.py`: Client session implementation
- `/fastmcp/server/proxy.py`: Proxy server and progress handlers
- `/fastmcp/server/context.py`: Request context and progress reporting
- `/fastmcp/server/dependencies.py`: Context management and retrieval
- `/fastmcp/client/transports.py`: Transport implementations including stdio

### FastMCP Version

- **Version**: 2.10.2 (from `pyproject.toml`)
- **Library location**: `.venv/lib/python3.13/site-packages/fastmcp/`

### Related Issues

This issue demonstrates a broader challenge in MCP proxy implementations: maintaining request context across different transport types. Similar issues may exist in other proxy scenarios where context isolation occurs.

---

**Investigation completed by**: Claude Code  
**Next steps**: Resume work on implementing FastMCP core fix or alternative workarounds  
**Priority**: Medium (affects progress notification functionality, workarounds available)