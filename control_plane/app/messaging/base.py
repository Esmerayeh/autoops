from typing import Protocol


class EventBus(Protocol):
    def publish(self, stream: str, key: str, payload: dict) -> str: ...
