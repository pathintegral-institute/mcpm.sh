from typing import Any, Protocol, TypedDict
from uuid import UUID, uuid4

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import types


class Session(TypedDict):
    id: UUID
    # some read,write streams related with session
    read_stream: MemoryObjectReceiveStream[types.JSONRPCMessage | Exception]
    read_stream_writer: MemoryObjectSendStream[types.JSONRPCMessage | Exception]

    write_stream: MemoryObjectSendStream[types.JSONRPCMessage]
    write_stream_reader: MemoryObjectReceiveStream[types.JSONRPCMessage]
    # any meta data is saved here
    meta: dict[str, Any]


class SessionStore(Protocol):

    def exist(self, session_id: UUID) -> bool:
        ...

    async def put(self, session: Session) -> None:
        ...

    async def get(self, session_id: UUID) -> Session:
        ...

    async def remove(self, session_id: UUID):
        ...

    async def cleanup(self):
        ...


class LocalSessionStore:

    def __init__(self):
        self._store: dict[UUID, Session] = {}

    def exist(self, session_id: UUID) -> bool:
        return session_id in self._store

    async def put(self, session: Session) -> None:
        self._store[session["id"]] = session

    async def get(self, session_id: UUID) -> Session:
        return self._store[session_id]

    async def remove(self, session_id: UUID):
        session = self._store.pop(session_id, None)
        if session:
            await session["read_stream_writer"].aclose()
            await session["write_stream"].aclose()

    async def cleanup(self):
        keys = list(self._store.keys())
        for session_id in keys:
            await self.remove(session_id)


class SessionManager:

    def __init__(self):
        self.session_store: SessionStore = LocalSessionStore()

    def exist(self, session_id: UUID) -> bool:
        return self.session_store.exist(session_id)

    async def create_session(self, meta: dict[str, Any] = {}) -> Session:
        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)
        session_id = uuid4()
        session = Session(
            id=session_id,
            read_stream=read_stream,
            read_stream_writer=read_stream_writer,
            write_stream=write_stream,
            write_stream_reader=write_stream_reader,
            meta=meta
        )
        await self.session_store.put(session)
        return session

    async def get_session(self, session_id: UUID) -> Session:
        return await self.session_store.get(session_id)

    async def close_session(self, session_id: UUID):
        await self.session_store.remove(session_id)

    async def cleanup_resources(self):
        await self.session_store.cleanup()
