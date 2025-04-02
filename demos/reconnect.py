import asyncio
from datetime import datetime
import logging

from lib.rcon import Rcon
from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT
from lib.exceptions import HLLError


async def main():
    rcon = Rcon(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )
    rcon.start()

    last_seen_time = datetime.fromtimestamp(0)
    while True:
        try:
            # Fetch logs from the past 10 seconds
            # TODO: Increase when bug is fixed
            logs = await rcon.commands.admin_log(seconds_span=5)
            
            latest_log_time: datetime | None = None
            for entry in logs['entries']:
                # This doesn't currently work, as the timestamp provided is incorrect.
                # It is the time that the command is executed, not the time that the log was generated.
                """
                # Parse log time
                latest_log_time = datetime.fromisoformat(entry['timestamp'].replace('.', '-'))

                # Skip if log was already seen
                if latest_log_time <= last_seen_time:
                    continue
                """

                # Print log in green
                print(f"| \033[92m{entry['message']}\033[0m")
            
            if latest_log_time:
                last_seen_time = latest_log_time

        except (HLLError, asyncio.TimeoutError) as e:
            logging.error("Failed to fetch logs: %s", type(e).__name__)

        await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
