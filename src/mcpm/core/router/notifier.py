import logging
from typing import Any, Awaitable, Callable

from mcpm.core.schema import ConfigType

logger = logging.getLogger(__name__)

CallableT = Callable[[ConfigType], Awaitable[Any]]

class ConfigUpdateNotifier:

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


    def __init__(self) -> None:
        """
        Initialize the ConfigUpdateNotifier singleton.

        This class implements the observer pattern to notify subscribers when configuration changes occur.
        Subscribers can register callbacks that will be executed when configuration updates are detected.
        """
        self._subscribers: list[CallableT] = []

    def subscribe(self, callback: CallableT):
        if callback not in self._subscribers:
            self._subscribers.append(callback)
        return lambda: self.unsubscribe(callback)

    def unsubscribe(self, callback: CallableT):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def notify_update(self, config_type: ConfigType):
        """ Notify all subscribers about the update """
        for subscriber in self._subscribers:
            try:
                await subscriber(config_type)
            except Exception as e:
                logger.error(f"Failed to notify subscriber due to error: {e}")
