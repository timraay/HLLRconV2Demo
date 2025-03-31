
import asyncio

from lib.client import RconClient
from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT


async def main():
    client = RconClient(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )
    
    async with client:
        responses = await asyncio.gather(
            client.commands.get_server_config(),
            client.commands.get_server_session(),
            client.commands.get_map_rotation(),
            client.commands.get_players()
        )

        print()
        for response in responses:
            print(response)
        print()

if __name__ == '__main__':
    asyncio.run(main())
