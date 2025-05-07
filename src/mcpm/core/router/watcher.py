"""
Configuration watchers for monitoring changes from different sources.
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from watchfiles import Change, awatch

from mcpm.core.router.notifier import ConfigUpdateNotifier
from mcpm.core.schema import ConfigType

logger = logging.getLogger(__name__)


class BaseConfigWatcher(ABC):
    """
    A base class for configuration watcher
    """

    def __init__(self, source_id: Any) -> None:
        self.source_id = source_id
        self.running = False
        self.watch_task: Optional[asyncio.Task] = None
        self.notifier: ConfigUpdateNotifier = ConfigUpdateNotifier.get_instance()

    async def start(self) -> Optional[asyncio.Task]:
        if not self.running:
            self.running = True
            self.watch_task = asyncio.create_task(self._watch_config())
            logger.info(f"Started watching config source: {self.source_id}")
            return self.watch_task
        return self.watch_task

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


    @abstractmethod
    async def _watch_config(self):
        pass


    async def notify_update(self, config_type: ConfigType):
        await self.notifier.notify_update(config_type)


class FileConfigWatcher(BaseConfigWatcher):

    def __init__(self, config_path: str) -> None:
        """
        FileConfigWatcher watches for changes in a local config file.

        Args:
            config_path: Path to the config file to watch
        """
        super().__init__(source_id=config_path)
        self.config_path = Path(config_path)

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
        updated = self._validate_config()
        if updated:
            logger.info("Config file has been modified, notifying subscribers...")
            await self.notify_update(ConfigType.FILE)

    def _validate_config(self):
        """Validate the config file format."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                _ = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing config file: {self.config_path}")
            return False
        else:
            return True


class CloudConfigWatcher(BaseConfigWatcher):

    def __init__(self, api_endpoint: str, poll_interval_ms: int = 1000) -> None:
        """
        CloudConfigWatcher watches for changes in a remote config file.

        Args:
            api_endpoint: API endpoint for polling remote config
            poll_interval_ms: Polling interval in milliseconds
        """
        super().__init__(source_id=api_endpoint)
        self.api_endpoint = api_endpoint
        self.poll_interval_ms = poll_interval_ms
        self.last_config_hash = None

    async def _watch_config(self):
        try:
            while self.running:
                config_data = await self._poll_remote_config()
                if config_data:
                    current_hash = hash(str(config_data))
                    if (self.last_config_hash is None) or (current_hash != self.last_config_hash):
                        self.last_config_hash = current_hash
                        await self.notify_update(ConfigType.CLOUD)

                await asyncio.sleep(self.poll_interval_ms)
        except asyncio.CancelledError:
            pass

    async def _poll_remote_config(self):
        return json.dumps({})
