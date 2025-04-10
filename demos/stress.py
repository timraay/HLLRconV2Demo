
import asyncio
import time

from lib.rcon import Rcon
from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT, validate_env


async def main():
    validate_env()
    rcon = Rcon(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )

    async with rcon:
        start_time = time.monotonic()
        responses = await asyncio.gather(*[
            rcon.commands.get_server_session()
            for _ in range(1000)
        ], return_exceptions=True)
        end_time = time.monotonic()

    print()
    print("Failed iterations:", ", ".join([
        str(i) for i, resp in enumerate(responses) if isinstance(resp, BaseException)
    ]) or "None")
    print(f"Took: {end_time - start_time:.3f} seconds")
    print()

if __name__ == '__main__':
    asyncio.run(main())
