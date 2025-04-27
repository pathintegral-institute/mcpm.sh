import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from watchfiles import Change, awatch

logger = logging.getLogger(__name__)


class ConfigWatcher:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.running = False
        self.reload_lock = asyncio.Lock()
        self.on_modification_callback: Optional[Callable[[], Awaitable[Any]]] = None
        self.watch_task: Optional[asyncio.Task] = None

    def register_modification_callback(self, fn: Callable[[], Awaitable[Any]]):
        if not self.on_modification_callback:
            self.on_modification_callback = fn

    def start(self):
        self.running = True
        self.watch_task = asyncio.create_task(self._watch_config())
        return self.watch_task

    async def _watch_config(self):
        try:
            async for changes in awatch(self.config_path):
                if not self.running:
                    break

                for change_type, file_path in changes:
                    if Path(file_path) == self.config_path:
                        if change_type in (Change.modified, Change.added):
                            await self._reload()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error watching config file: {e}")

    async def _reload(self):
        async with self.reload_lock:
            updated = self._validate_config()
            if updated:
                if self.on_modification_callback:
                    logger.info("Config file has been modified, reloading...")
                    await self.on_modification_callback()

    def _validate_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                _ = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing config file: {self.config_path}")
            return False
        else:
            return True

    async def stop(self):
        if self.running:
            self.running = False
            if self.watch_task and not self.watch_task.done():
                self.watch_task.cancel()
                try:
                    await self.watch_task
                    logger.info("Watcher stopped")
                except asyncio.CancelledError:
                    pass
