from typing import Protocol


class Collector(Protocol):
    name: str

    def collect(self) -> dict: ...
