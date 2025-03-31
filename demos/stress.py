
import asyncio

from lib.client import RconClient
from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT


async def main():
    rcon = RconClient(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )

    async with rcon:
        responses = await asyncio.gather(*[
            rcon.execute(
                command="ServerInformation",
                version=2,
                body={"Name": "players", "Value": ""},
            )
            for _ in range(1000)
        ], return_exceptions=True)

    for i, resp in enumerate(responses):
        if isinstance(resp, BaseException):
            print(i)

if __name__ == '__main__':
    asyncio.run(main())
