
from enum import IntEnum
import itertools
import json
import struct
from typing import ClassVar

from lib.constants import DO_USE_REQUEST_HEADERS, HEADER_FORMAT
from lib.exceptions import HLLCommandError

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
    def content_dict(self) -> dict:
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
            raise HLLCommandError(self.status_code, self.status_message)
