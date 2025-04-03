import asyncio
import logging
from demos.capture_position_data import main as start_capture


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(module)s.%(funcName)s:%(lineno)s] %(message)s',
)

args = [
    # Add servers here
    {
        "host": "127.0.0.1",
        "port": 7779,
        "password": "password"
    },
    ...
]

async def main():
    tasks = []
    for kwargs in args:
        task = asyncio.create_task(start_capture(**kwargs))
        tasks.append(task)
        await asyncio.sleep(3) # Prevent duplicate file names
    await asyncio.wait(tasks)

if __name__ == '__main__':
    asyncio.run(main())
