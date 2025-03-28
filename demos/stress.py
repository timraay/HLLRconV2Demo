
import asyncio

from constants import RCON_HOST, RCON_PASSWORD, RCON_PORT
from protocol import HLLRconV2Protocol


async def main():
    protocol = await HLLRconV2Protocol.connect(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )

    responses = await asyncio.gather(*[
        protocol.execute(
            command="ServerInformation",
            version=2,
            content_body={"Name": "players", "Value": ""},
        )
        for _ in range(1000)
    ], return_exceptions=True)

    for i, resp in enumerate(responses):
        if isinstance(resp, BaseException):
            print(i)

if __name__ == '__main__':
    asyncio.run(main())
