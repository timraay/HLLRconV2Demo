import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(".env")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

RCON_HOST: str = os.getenv("RCON_HOST", "")
RCON_PORT: int = int(os.getenv("RCON_PORT", 0))
RCON_PASSWORD: str = os.getenv("RCON_PASSWORD", "")

if not RCON_HOST:
    raise Exception("Missing RCON_HOST environment variable")
if not RCON_PORT:
    raise Exception("Missing RCON_PORT environment variable")
if not RCON_PASSWORD:
    raise Exception("Missing RCON_PASSWORD environment variable")
