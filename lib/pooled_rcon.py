import asyncio
import functools
import logging
import time
from lib.commands import RconCommands
from lib.rcon import Rcon
from lib.abc import RconClient
from lib.exceptions import HLLCommandError, HLLConnectionError

@functools.total_ordering
class QueuedCommand:
    def __init__(
        self,
        command: str,
        version: int,
        body: str | dict = "",
        attempts: int = 1,
    ) -> None:
        self.command = command
        self.version = version
        self.body = body
        self.attempts = attempts

        self._result: asyncio.Future[str] = asyncio.Future()
        self._submit_time = time.monotonic()
    
    def set_result(self, value: str) -> None:
        self._result.set_result(value)
    
    def set_exception(self, exception: Exception) -> None:
        self._result.set_exception(exception)
    
    def __await__(self):
        return self._result.__await__()
    
    def __eq__(self, other):
        if isinstance(other, QueuedCommand):
            return self._submit_time == other._submit_time
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, QueuedCommand):
            return self._submit_time < other._submit_time
        return NotImplemented

class RconWorker(RconClient):
    def __init__(self, pool: 'PooledRcon') -> None:
        self.pool = pool
        self.rcon = Rcon(
            host=pool.host,
            port=pool.port,
            password=pool.password,
            logger=pool.logger,
        )
        self._task: asyncio.Task | None = None
    
    def is_started(self) -> bool:
        return self.rcon.is_started() and self._is_task_started()

    def is_connected(self) -> bool:
        return self.rcon.is_connected()

    async def wait_until_connected(self, timeout: float | None = None) -> None:
        return await self.rcon.wait_until_connected(timeout=timeout)

    def _is_task_started(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        self.rcon.start()
        if not self._is_task_started():
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        self.rcon.stop()
        if self._is_task_started():
            assert self._task is not None
            self._task.cancel()
        self._task = None

    async def execute(self, command: str, version: int, body: str | dict = "") -> str:
        return await self.rcon.execute(
            command=command,
            version=version,
            body=body,
        )
    
    async def _loop(self):
        while True:
            try:
                try:
                    await self.wait_until_connected()
                except HLLConnectionError:
                    if not self.rcon.is_started():
                        # The connection was stopped
                        self.pool.logger.warning("Worker %r exiting prematurely due to client having been stopped", self)
                        return
                    await asyncio.sleep(0.5)
                    continue

                priority, entry = await self.pool._queue.get()
                if not self.is_connected():
                    # We lost connection while waiting. Put entry back at the front of the queue.
                    self.pool.enqueue(entry, priority=max(priority - 1, 1))
                
                else:
                    try:
                        response = await self.execute(
                            command=entry.command,
                            version=entry.version,
                            body=entry.body,
                        )
                    except HLLConnectionError:
                        # We lost connection while executing the command. Enqueue it again.
                        self.pool.enqueue(entry, priority=max(priority - 1, 1))
                    except HLLCommandError as e:
                        # Command failed. Put back in the queue if we have any attempts remaining.
                        if entry.attempts > 1:
                            entry.attempts -= 1
                            self.pool.enqueue(entry, priority=max(priority - 1, 1))
                        else:
                            entry.set_exception(e)
                    else:
                        entry.set_result(response)

            except asyncio.CancelledError:
                return
            
            except:
                self.pool.logger.exception("Worker %r encountered unexpected error", self)
                await asyncio.sleep(1) # Go easy

class PooledRcon(RconClient):
    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        pool_size: int,
        logger: logging.Logger = logging # type: ignore
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.pool_size = pool_size
        self.logger = logger

        self.commands = RconCommands(self)

        self._workers: list[RconWorker] = []
        self._queue: asyncio.PriorityQueue[tuple[int, QueuedCommand]] = asyncio.PriorityQueue()
    
    def is_started(self):
        return any(
            worker.is_started()
            for worker in self._workers
        )

    def is_connected(self):
        return any(
            worker.is_connected()
            for worker in self._workers
        )

    async def wait_until_connected(self, timeout: float | None = None):
        if not self._workers:
            raise HLLConnectionError("Connection is closed")
        
        for f in asyncio.as_completed(
            [worker.wait_until_connected() for worker in self._workers],
            timeout=timeout
        ):
            try:
                await f
            except HLLConnectionError:
                pass
            else:
                return
            
        raise HLLConnectionError("All workers are disconnected")

    def start(self):
        if self.is_started():
            self.stop()
        
        self._workers = [
            RconWorker(self)
            for _ in range(self.pool_size)
        ]
        for worker in self._workers:
            worker.start()

    def stop(self):
        for worker in self._workers:
            worker.stop()
        self._workers.clear()

    def update_connection(self):
        # Restart the connection
        if self.is_started():
            self.start()

    def enqueue(self, entry: QueuedCommand, priority: int = 10) -> None:
        self._queue.put_nowait((priority, entry))

    async def execute(self, command: str, version: int, body: str | dict = "") -> str:
        entry = QueuedCommand(
            command=command,
            version=version,
            body=body,
            attempts=2,
        )
        self.enqueue(entry)
        return await entry
