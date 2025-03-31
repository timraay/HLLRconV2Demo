
import asyncio

from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT
from lib.protocol import HLLRconV2Protocol


async def main():
    protocol = await HLLRconV2Protocol.connect(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )
    
    responses = await asyncio.gather(
        protocol.execute("ServerInformation", 2, {"Name": "serverconfig", "Value": ""}),
        protocol.execute("ServerInformation", 2, {"Name": "session", "Value": ""}),
        protocol.execute("ServerInformation", 2, {"Name": "maprotation", "Value": ""}),
        protocol.execute("ServerInformation", 2, {"Name": "players", "Value": ""}),
    )

    for response in responses:
        response.raise_for_status()

    print()
    for response in responses:
        print(response.content_dict)
    print()

if __name__ == '__main__':
    asyncio.run(main())
