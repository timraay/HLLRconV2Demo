from abc import ABC, abstractmethod

class RconExecutor(ABC):
    @abstractmethod
    async def execute(self, command: str, version: int, body: str | dict = "") -> str:
        ...
