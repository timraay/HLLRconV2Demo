import array
import asyncio
import base64
from collections import deque
import logging
import struct
from typing import Any, Callable, Self

from lib.constants import DO_POP_V1_XORKEY, DO_WAIT_BETWEEN_REQUESTS, DO_USE_REQUEST_HEADERS, HEADER_FORMAT
from lib.exceptions import HLLConnectionError, HLLConnectionLostError
from lib.models import RconRequest, RconResponse

class HLLRconV2Protocol(asyncio.Protocol):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        timeout: float | None = None,
        logger: logging.Logger = logging, # type: ignore
        on_connection_lost: Callable[[Exception | None], Any] | None = None,
    ):
        self._transport: asyncio.Transport | None = None
        self._buffer: bytes = b""

        if DO_USE_REQUEST_HEADERS:
            self._waiters: dict[int, asyncio.Future[RconResponse]] = {}
        else:
            self._queue: deque[asyncio.Future[RconResponse]] = deque()
        
        self._lock = asyncio.Lock()
        
        if DO_POP_V1_XORKEY:
            self._seen_v1_xorkey: bool = False

        self.loop = loop
        self.timeout = timeout
        self.logger = logger
        self.on_connection_lost = on_connection_lost

        self.xorkey: bytes | None = None
        self.auth_token: str | None = None

    @classmethod
    async def _connect(
        cls,
        host: str,
        port: int,
        timeout: float | None = 10,
        loop: asyncio.AbstractEventLoop | None = None,
        logger: logging.Logger = logging, # type: ignore
        on_connection_lost: Callable[[Exception | None], Any] | None = None,
    ):
        loop = loop or asyncio.get_event_loop()
        protocol_factory = lambda: cls(
            loop=loop,
            timeout=timeout,
            logger=logger,
            on_connection_lost=on_connection_lost,
        )

        try:
            _, protocol = await asyncio.wait_for(
                loop.create_connection(protocol_factory, host=host, port=port),
                timeout=15
            )
        except asyncio.TimeoutError:
            raise Exception("Address %s could not be resolved" % host)
        except ConnectionRefusedError:
            raise Exception("The server refused connection over port %s" % port)

        logger.info("Connected!")
        return protocol

    @classmethod
    async def connect(
        cls,
        host: str,
        port: int,
        password: str,
        timeout: float | None = 10,
        loop: asyncio.AbstractEventLoop | None = None,
        logger: logging.Logger = logging, # type: ignore
        on_connection_lost: Callable[[Exception | None], Any] | None = None,
    ) -> Self:
        protocol = await cls._connect(
            host=host,
            port=port,
            timeout=timeout,
            loop=loop,
            logger=logger,
            on_connection_lost=on_connection_lost,
        )
        await protocol.authenticate(password)
        return protocol
    
    def disconnect(self):
        if self._transport:
            self._transport.close()

    def is_connected(self):
        return self._transport is not None

    def connection_made(self, transport):
        self.logger.info('Connection made! Transport: %s', transport)
        self._transport = transport # type: ignore

    def data_received(self, data: bytes):
        self.logger.debug("Incoming: (%s) %s", self._xor(data).count(b"\t"), data[:10])

        if DO_POP_V1_XORKEY:
            if not self._seen_v1_xorkey:
                self.logger.info("Ignoring V1 XOR-key: %s", data[:4])
                self._seen_v1_xorkey = True
                data = data[4:]
                if not data:
                    return

        self._buffer += data
        self._read_from_buffer()

    def _read_from_buffer(self):
        pkt_id: int
        pkt_len: int

        # Read header
        header_len = struct.calcsize(HEADER_FORMAT)
        if len(self._buffer) < header_len:
            self.logger.debug("Buffer too small (%s < %s)", len(self._buffer), header_len)
            return
        # pkt_id, pkt_len = struct.unpack(HEADER_FORMAT, self._xor(self._buffer[:header_len]))
        pkt_id, pkt_len = struct.unpack(HEADER_FORMAT, self._buffer[:header_len])
        pkt_size = header_len + pkt_len
        self.logger.debug("pkt_id = %s, pkt_len = %s", pkt_id, pkt_len)

        # Check whether whole packet is on buffer
        if len(self._buffer) >= pkt_size:
            # Read packet data from buffer
            # decoded_body = self._xor(self._buffer[header_len:pkt_size], offset=header_len)
            decoded_body = self._xor(self._buffer[header_len:pkt_size])
            self.logger.debug("Unpacking: %s", decoded_body)
            pkt = RconResponse.unpack(pkt_id, decoded_body)
            self._buffer = self._buffer[pkt_size:]
            
            # Respond to waiter
            if DO_USE_REQUEST_HEADERS:
                waiter = self._waiters.pop(pkt_id, None)
                if not waiter:
                    self.logger.warning("No waiter for packet with ID %s", pkt_id)
                else:
                    waiter.set_result(pkt)
            else:
                if not self._queue:
                    self.logger.warning("No waiter for packet with ID %s", pkt_id)
                else:
                    waiter = self._queue.popleft()
                    waiter.set_result(pkt)
            
            # Repeat if buffer is not empty; Another complete packet might be on it
            if self._buffer:
                self._read_from_buffer()
    
    def connection_lost(self, exc):
        self._transport = None

        if DO_USE_REQUEST_HEADERS:
            waiters = list(self._waiters.values())
            self._waiters.clear()
        else:
            waiters = list(self._queue)
            self._queue.clear()

        if exc:
            self.logger.warning('Connection lost: %s', exc)
            for waiter in waiters:
                if not waiter.done():
                    waiter.set_exception(HLLConnectionLostError(str(exc)))

        else:
            self.logger.info('Connection closed')
            for waiter in waiters:
                waiter.cancel()

        if self.on_connection_lost:
            try:
                self.on_connection_lost(exc)
            except:
                if self.logger:
                    self.logger.exception("Failed to invoke on_connection_lost hook")

    def _xor(self, message: bytes, offset: int = 0) -> bytes:
        """Encrypt or decrypt a message using the XOR key provided by the game server"""
        if not self.xorkey:
            return message
            
        n = []
        for i in range(len(message)):
            n.append(message[i] ^ self.xorkey[(i + offset) % len(self.xorkey)])

        res = array.array('B', n).tobytes()
        assert len(res) == len(message)
        return res
    
    async def execute(self, command: str, version: int, content_body: dict | str = "") -> RconResponse:
        if not self._transport:
            raise HLLConnectionError("Connection is closed")

        # Create request
        request = RconRequest(
            command=command,
            version=version,
            auth_token=self.auth_token,
            content_body=content_body,
        )

        # Potentially wait before sending request, ensures there is a fixed-length
        # delay between concurrent requests
        if DO_WAIT_BETWEEN_REQUESTS > 0:
            self.logger.debug("Request %s acquiring lock...", request.id)
            await self._lock.acquire()
            self.logger.debug("Request %s acquired lock!", request.id)
            self.loop.call_later(DO_WAIT_BETWEEN_REQUESTS, lambda: self._lock.release())
        else:
            await self._lock.acquire()

        # Send request
        packed = request.pack()
        message = self._xor(packed)
        self.logger.debug("Writing: %s", packed)
        self._transport.write(message)

        # Create waiter for response
        waiter: asyncio.Future[RconResponse] = self.loop.create_future()
        if DO_USE_REQUEST_HEADERS:
            self._waiters[request.id] = waiter
        else:
            self._queue.append(waiter)

        try:
            # Wait for response
            response = await asyncio.wait_for(waiter, timeout=self.timeout)
            self.logger.debug("Response: (%s) %s", response.name, response.content_body)
            return response
        finally:
            # Cleanup waiter
            waiter.cancel()

            if DO_USE_REQUEST_HEADERS:
                self._waiters.pop(request.id, None)
            else:
                try:
                    self._queue.remove(waiter)
                except ValueError:
                    pass

            if DO_WAIT_BETWEEN_REQUESTS <= 0:
                self._lock.release()

    async def authenticate(self, password: str):
        self.logger.debug('Waiting to login...')
        
        xorkey_resp = await self.execute("ServerConnect", 2, "")
        xorkey_resp.raise_for_status()
        self.logger.info("Received xorkey")

        assert isinstance(xorkey_resp.content_body, str)
        self.xorkey = base64.b64decode(xorkey_resp.content_body)

        auth_token_resp = await self.execute("Login", 2, password)
        auth_token_resp.raise_for_status()
        self.logger.info("Received auth token, successfully authenticated")

        self.auth_token = auth_token_resp.content_body

