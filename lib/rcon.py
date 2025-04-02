import asyncio
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from lib.commands import RconCommands
from lib.exceptions import HLLConnectionError, HLLError
from lib.abc import RconClient
from lib.protocol import HLLRconV2Protocol
from lib.utils import safe_create_task

BACKOFF_MIN = 0.5
BACKOFF_MAX = 30.0
BACKOFF_FACTOR = 1.618

class Rcon(RconClient):
    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        logger: logging.Logger = logging # type: ignore
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.logger = logger

        self.commands = RconCommands(self)

        self._sock_task: asyncio.Task | None = None
        # This future can have one of four states:
        # - Pending: The socket is trying to connect
        # - Cancelled: The socket is/was disabled
        # - Exception: The connection was rejected
        # - Done: The socket is connected
        self._sock: asyncio.Future[HLLRconV2Protocol] = asyncio.Future()
        self._sock.cancel()
        self._sock_disconnect_event = asyncio.Event()

    def is_started(self):
        return self._sock_task is not None

    def is_connected(self):
        return self._sock.done() and not self._sock.cancelled() and not self._sock.exception()

    async def wait_until_connected(self, timeout: float | None = None) -> None:
        try:
            await asyncio.wait_for(asyncio.shield(self._sock), timeout=timeout)
        except asyncio.CancelledError:
            raise HLLConnectionError("Connection is closed")

    def _handle_connection_loss(self, exc: Exception | None):
        self._sock_disconnect_event.set()
        self._sock_disconnect_event.clear()

    def start(self):
        if self.is_started():
            self.stop()
        
        self._sock_task = safe_create_task(
            self._sock_loop(),
            err_msg=f"RconClient failed to connect and was stopped",
            logger=self.logger,
            name=f"RconClient[{self.host}:{self.port}]"
        )
        self._sock = asyncio.Future()

    def stop(self):
        if self._sock_task:
            self._sock_task.cancel()
            self._sock_task = None
        self._sock.cancel()

    def update_connection(self):
        # Restart the connection
        if self.is_started():
            self.start()

    @asynccontextmanager
    async def _connect(self, timeout: float = 10):
        protocol = await HLLRconV2Protocol._connect(
            host=self.host,
            port=self.port,
            timeout=timeout,
            logger=self.logger,
            on_connection_lost=self._handle_connection_loss,
        )

        try:
            await protocol.authenticate(self.password)
            yield protocol
        finally:
            protocol.disconnect()


    # async with ...
    async def __aenter__(self):
        if self.is_connected():
            raise RuntimeError("RconClient is already connected")

        self._sock = asyncio.Future()
        protocol = await HLLRconV2Protocol.connect(
            host=self.host,
            port=self.port,
            password=self.password,
            logger=self.logger,
            on_connection_lost=self._handle_connection_loss,
        )
        try:
            self._sock.set_result(protocol)
            return protocol
        except:
            protocol.disconnect()
            raise

    async def __aexit__(self, exc_type, exc, tb):
        if self.is_connected():
            protocol = self._sock.result()
            protocol.disconnect()
            self._sock = asyncio.Future()


    # async for ... in self
    async def __aiter__(self) -> AsyncIterator[HLLRconV2Protocol]:
        backoff_delay = BACKOFF_MIN
        while True:
            try:
                async with self._connect() as protocol:
                    yield protocol
            except Exception as e:
                self.logger.info("Socket connection failed; retrying in %d seconds", int(backoff_delay))
                await asyncio.sleep(int(backoff_delay))
                # Increase delay with truncated exponential backoff.
                backoff_delay = backoff_delay * BACKOFF_FACTOR
                backoff_delay = min(backoff_delay, BACKOFF_MAX)
                continue
            else:
                # Connection succeeded - reset backoff delay
                backoff_delay = BACKOFF_MIN

    async def _sock_loop(self):
        try:
            try:
                # Automatically reconnect with exponential backoff
                async for sock in self:
                    try:
                        # Once connected change the future to done
                        self._sock.set_result(sock)
                        # Wait until socket disconnects
                        await self._sock_disconnect_event.wait()
                    finally:
                        # Change the sock to pending again while we reconnect
                        self._sock = asyncio.Future()
            except HLLError as e:
                # This shouldn't realistically happen
                self._sock.set_exception(e)

        finally:
            self._sock_task = None

            # When exiting the loop, stop the task and cancel the future
            if not self._sock.done():
                self._sock.cancel()
            
            # Propagate fatal websocket errors to the websocket task
            if e := self._sock.exception():
                raise e

    async def execute(self, command: str, version: int, body: str | dict = "") -> str:
        await self.wait_until_connected(timeout=5)
        protocol = self._sock.result()
        response = await protocol.execute(command=command, version=version, content_body=body)
        response.raise_for_status()
        return response.content_body
