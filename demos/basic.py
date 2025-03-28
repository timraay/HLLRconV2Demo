
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
            content_body=content_body,
        )
        for content_body in [
            {"Name": "players", "Value": ""},
            {"Name": "session", "Value": ""},
            {"Name": "serverconfig", "Value": ""},
            {"Name": "maprotation", "Value": ""},
        ]
    ])

    for resp in responses:
        print(resp)

if __name__ == '__main__':
    asyncio.run(main())
