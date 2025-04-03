import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper
import asyncio
from datetime import datetime
import logging
from pathlib import Path
from typing import NamedTuple

from lib.rcon import Rcon
from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT
from lib.exceptions import HLLError
from lib.responses import PlayerTeam

POSITIONS_DIR = Path("data/positions/")
DEATHS_DIR = Path("data/deaths/")

class Position(NamedTuple):
    x: int
    y: int
    z: int

class Row(NamedTuple):
    timestamp: int
    team_id: int
    x: int
    y: int
    z: int

class Match:
    def __init__(self) -> None:
        self.name = "Unknown"
        self.start_time = datetime.now()
        self.positions_file: AsyncTextIOWrapper | None = None
        self.deaths_file: AsyncTextIOWrapper | None = None

    def is_ongoing(self):
        return self.positions_file is not None

    async def start(self, name: str):
        assert self.positions_file is None

        logging.info("Starting match: %s", name)

        self.name = name
        self.start_time = datetime.now()

        fn = f"{self.name.replace(' ', '_')}_{int(self.start_time.timestamp())}.csv"

        self.positions_file = await aiofiles.open(POSITIONS_DIR / Path(fn), "w+")
        self.deaths_file = await aiofiles.open(DEATHS_DIR / Path(fn), "w+")
        await self.positions_file.write("timestamp,team_id,x,y,z\n")
        await self.deaths_file.write("timestamp,team_id,x,y,z\n")

    async def end(self):
        assert self.positions_file is not None
        assert self.deaths_file is not None

        logging.info("Ending match: %s", self.name)

        await self.positions_file.close()
        await self.deaths_file.close()
        self.positions_file = None
        self.deaths_file = None

        player_initial_positions.clear()
        player_past_positions.clear()
    
    async def add_positions(self, rows: list[Row]):
        assert self.positions_file is not None
        await self.positions_file.writelines([
            ",".join([str(x) for x in row]) + "\n"
            for row in rows
        ])

    async def add_deaths(self, rows: list[Row]):
        assert self.deaths_file is not None
        await self.deaths_file.writelines([
            ",".join([str(x) for x in row]) + "\n"
            for row in rows
        ])
    
    async def update_status(self, rcon: Rcon):
        logs = await rcon.commands.admin_log(seconds_span=20, filter="MATCH ")
        if self.is_ongoing():
            for log in logs["entries"]:
                if ")] MATCH ENDED " in log["message"]:
                    await self.end()
        else:
            for log in logs["entries"]:
                if ")] MATCH START " in log["message"]:
                    name = log["message"].split("MATCH START ", 1)[-1]
                    await self.start(name)


player_initial_positions: dict[str, Position | None] = {}
player_past_positions: dict[str, Position] = {}

async def analyze_positions(rcon: Rcon, match: Match) -> None:
    players = await rcon.commands.get_players()
    timestamp = int(datetime.now().timestamp())
    positions: list[Row] = []
    deaths: list[Row] = []

    for player in players["players"]:
        raw_pos = player["worldPosition"]
        pos = Position(
            x=int(raw_pos["x"]),
            y=int(raw_pos["y"]),
            z=int(raw_pos["z"]),
        )

        player_id = player["iD"]
        initial_pos = player_initial_positions.setdefault(player_id, pos)
        if initial_pos is not None and pos == initial_pos:
            continue

        team_id = faction_to_team_id(player["team"])
        
        is_dead = (pos.x == 0 and pos.y == 0 and pos.z == 0)
        if is_dead:
            past_pos = player_past_positions.get(player_id)
            if past_pos and past_pos != pos:
                deaths.append(Row(
                    timestamp,
                    team_id,
                    x=past_pos.x,
                    y=past_pos.y,
                    z=past_pos.z,
                ))

        else:
            player_initial_positions[player_id] = None
            positions.append(Row(
                timestamp,
                team_id,
                x=pos.x,
                y=pos.y,
                z=pos.z,
            ))
        
        player_past_positions[player_id] = pos
    
    if positions:
        await match.add_positions(positions)
    if deaths:
        await match.add_deaths(deaths)

def faction_to_team_id(faction: PlayerTeam):
    if (faction == PlayerTeam.GER) or (faction == PlayerTeam.DAK):
        return 2
    else:
        return 1

async def main(
    host: str | None = None,
    port: int | None = None,
    password: str | None = None,
):
    POSITIONS_DIR.mkdir(exist_ok=True, parents=True)
    DEATHS_DIR.mkdir(exist_ok=True)

    rcon = Rcon(
        host=host or RCON_HOST,
        port=port or RCON_PORT,
        password=password or RCON_PASSWORD,
    )
    rcon.start()

    match = Match()
    await match.start("Unknown")

    try:
        while True:
            try:
                if match.is_ongoing():
                    await analyze_positions(rcon, match)

                await match.update_status(rcon)

            except (HLLError, asyncio.TimeoutError) as e:
                logging.error("Failed to perform iteration: %s", type(e).__name__)
            except:
                logging.exception("Unknown exception")

            await asyncio.sleep(0)
    
    finally:
        if match.is_ongoing():
            assert match.positions_file is not None
            await match.end()

if __name__ == '__main__':
    asyncio.run(main())
