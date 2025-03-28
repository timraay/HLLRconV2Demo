import array
import asyncio
import base64
from collections import deque
from enum import IntEnum
import itertools
import json
import logging
import struct
from typing import ClassVar, Final, Self

HEADER_FORMAT = "<II"
DO_XOR_RESPONSES: Final[bool] = False
DO_USE_REQUEST_HEADERS: Final[bool] = False

class RconResponseStatus(IntEnum):
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    INTERNAL_ERROR = 500

class RconRequest:
    __uid: ClassVar[itertools.count] = itertools.count(start=1)

    def __init__(self, command: str, version: int, auth_token: str | None, content_body: dict | str = ""):
        self.name = command
        self.version = version
        self.auth_token = auth_token
        self.content_body = content_body
        self.id = next(self.__uid)

    def pack(self) -> bytes:
        body = {
            "authToken": self.auth_token or "",
            "version": self.version,
            "name": self.name,
            "contentBody": (
                self.content_body
                if isinstance(self.content_body, str)
                else json.dumps(self.content_body)
            )
        }
        body_encoded = json.dumps(body).encode()
        if DO_USE_REQUEST_HEADERS:
            header = struct.pack(HEADER_FORMAT, self.id, len(body_encoded))
            return header + body_encoded
        else:
            return body_encoded

class RconResponse:
    def __init__(self, id: int, command: str, version: int, status_code: RconResponseStatus, status_message: str, content_body: str):
        self.id = id
        self.name = command
        self.version = version
        self.status_code = status_code
        self.status_message = status_message
        self.content_body = content_body
    
    @property
    def content_dict(self):
        return json.loads(self.content_body)
    
    def __str__(self):
        try:
            content = self.content_dict
        except json.JSONDecodeError:
            content = self.content_body

        return f"{self.status_code} {self.name} {content}"

    @classmethod
    def unpack(cls, id: int, body_encoded: bytes):
        body = json.loads(body_encoded)
        return cls(
            id=id,
            command=str(body["name"]),
            version=int(body["version"]),
            status_code=RconResponseStatus(int(body["statusCode"])),
            status_message=str(body["statusMessage"]),
            content_body=body["contentBody"],
        )
    
    def raise_for_status(self):
        if self.status_code != RconResponseStatus.OK:
            raise Exception("RCON %s: %s" % (self.status_code, self.status_message))

class HLLRconV2Protocol(asyncio.Protocol):
    def __init__(self, loop: asyncio.AbstractEventLoop, timeout: float | None = None):
        self._transport: asyncio.Transport | None = None
        self._loop = loop

        if DO_USE_REQUEST_HEADERS:
            self._waiters: dict[int, asyncio.Future[RconResponse]] = {}
        else:
            self._waiters: deque[asyncio.Future[RconResponse]] = deque()

        self._buffer: bytes = b""
        self.timeout = timeout
        self.xorkey: bytes | None = None
        self.auth_token: str | None = None

    @classmethod
    async def connect(
        cls,
        host: str,
        port: int,
        password: str,
        timeout: float | None = 10,
        loop: asyncio.AbstractEventLoop | None = None
    ) -> Self:
        loop = loop or asyncio.get_event_loop()
        protocol_factory = lambda: cls(loop=loop, timeout=timeout)

        try:
            _, protocol = await asyncio.wait_for(
                loop.create_connection(protocol_factory, host=host, port=port),
                timeout=15
            )
        except asyncio.TimeoutError:
            raise Exception("Address %s could not be resolved" % host)
        except ConnectionRefusedError:
            raise Exception("The server refused connection over port %s" % port)

        logging.info("Connected!")

        # RCON V1 sends a XOR key upon connecting. Clear this from the buffer.
        await asyncio.sleep(0.2)
        protocol._buffer = b""

        await protocol.authenticate(password)

        return protocol

    def is_connected(self):
        return self._transport is not None

    def connection_made(self, transport):
        logging.info('Connection made! Transport: %s', transport)
        self._transport = transport # type: ignore

    def data_received(self, data: bytes):
        logging.debug("Incoming: (%s) %s", self._xor(data).count(b"\t"), data[:10])
        self._buffer += data
        self._read_from_buffer()

    def _read_from_buffer(self):
        pkt_id: int
        pkt_len: int

        # Read header
        header_len = struct.calcsize(HEADER_FORMAT)
        if len(self._buffer) < header_len:
            logging.debug("Buffer too small (%s < %s)", len(self._buffer), header_len)
            return
        # pkt_id, pkt_len = struct.unpack(HEADER_FORMAT, self._xor(self._buffer[:header_len]))
        pkt_id, pkt_len = struct.unpack(HEADER_FORMAT, self._buffer[:header_len])
        pkt_size = header_len + pkt_len
        logging.debug("pkt_id = %s, pkt_len = %s", pkt_id, pkt_len)

        # Check whether whole packet is on buffer
        if len(self._buffer) >= pkt_size:
            # Read packet data from buffer
            # decoded_body = self._xor(self._buffer[header_len:pkt_size], offset=header_len)
            decoded_body = self._xor(self._buffer[header_len:pkt_size])
            logging.debug("Unpacking: %s", decoded_body)
            pkt = RconResponse.unpack(pkt_id, decoded_body)
            self._buffer = self._buffer[pkt_size:]
            
            # Respond to waiter
            if DO_USE_REQUEST_HEADERS:
                waiter = self._waiters.pop(pkt_id, None)
                if not waiter:
                    logging.warning("No waiter for packet with ID %s", pkt_id)
                else:
                    waiter.set_result(pkt)
            else:
                if not self._waiters:
                    logging.warning("No waiter for packet with ID %s", pkt_id)
                else:
                    waiter = self._waiters.popleft()
                    waiter.set_result(pkt)
            
            # Repeat if buffer is not empty; Another complete packet might be on it
            if self._buffer:
                self._read_from_buffer()
    
    def connection_lost(self, exc):
        self._transport = None

        if DO_USE_REQUEST_HEADERS:
            waiters = list(self._waiters.values())
        else:
            waiters = list(self._waiters)

        if exc:
            logging.warning('Connection lost: %s', exc)
            for waiter in waiters:
                if not waiter.done():
                    waiter.set_exception(exc)
            self._waiters.clear()
            raise Exception("Connection lost")

        else:
            logging.info('Connection closed')
            for waiter in waiters:
                waiter.cancel()
            self._waiters.clear()

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
            raise Exception("Connection is closed")

        # Send request
        request = RconRequest(
            command=command,
            version=version,
            auth_token=self.auth_token,
            content_body=content_body,
        )
        packed = request.pack()
        message = self._xor(packed)
        logging.debug("Writing: %s", packed)
        self._transport.write(message)

        # Create waiter for response
        waiter: asyncio.Future[RconResponse] = self._loop.create_future()
        if DO_USE_REQUEST_HEADERS:
            self._waiters[request.id] = waiter
        else:
            self._waiters.append(waiter)

        try:
            # Wait for response
            response = await asyncio.wait_for(waiter, timeout=self.timeout)
            logging.debug("Response: (%s) %s", response.name, response.content_body)
            return response
        finally:
            # Cleanup waiter
            waiter.cancel()
            if DO_USE_REQUEST_HEADERS:
                self._waiters.pop(request.id, None)
            else:
                try:
                    self._waiters.remove(waiter)
                except ValueError:
                    pass

    async def authenticate(self, password: str):
        logging.debug('Waiting to login...')
        
        xorkey_resp = await self.execute("ServerConnect", 2, "")
        xorkey_resp.raise_for_status()
        logging.info("Received xorkey")

        assert isinstance(xorkey_resp.content_body, str)
        self.xorkey = base64.b64decode(xorkey_resp.content_body)

        auth_token_resp = await self.execute("Login", 2, password)
        auth_token_resp.raise_for_status()
        logging.info("Received auth token, successfully authenticated")

        self.auth_token = auth_token_resp.content_body

