import os
from pathlib import Path
from typing import Final
from dotenv import load_dotenv

ENV_PATH = Path(".env")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

RCON_HOST: Final[str] = os.getenv("RCON_HOST", "")
RCON_PORT: Final[int] = int(os.getenv("RCON_PORT", 0))
RCON_PASSWORD: Final[str] = os.getenv("RCON_PASSWORD", "")

if not RCON_HOST:
    raise Exception("Missing RCON_HOST environment variable")
if not RCON_PORT:
    raise Exception("Missing RCON_PORT environment variable")
if not RCON_PASSWORD:
    raise Exception("Missing RCON_PASSWORD environment variable")

DO_XOR_RESPONSES: Final[bool] = False
DO_USE_REQUEST_HEADERS: Final[bool] = False
DO_POP_V1_XORKEY: Final[bool] = True

HEADER_FORMAT = "<II"
DO_WAIT_BETWEEN_REQUESTS: float = 0.0
