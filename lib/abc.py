from abc import ABC, abstractmethod

class RconExecutor(ABC):
    @abstractmethod
    async def execute(self, command: str, version: int, body: str | dict = "") -> str:
        ...

class RconClient(RconExecutor, ABC):
    @abstractmethod
    def is_started(self) -> bool:
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...

    @abstractmethod
    async def wait_until_connected(self, timeout: float | None = None) -> None:
        ...

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...
