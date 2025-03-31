import asyncio
import logging
from typing import Coroutine

def safe_create_task(
        coro: Coroutine,
        err_msg: str | None = None,
        name: str | None = None,
        logger: logging.Logger = logging # type: ignore
):
    def _task_inner(t: asyncio.Task):
        if t.cancelled():
            logger.warning(f"Task {task.get_name()} was cancelled")
        elif exc := t.exception():
            logger.error(
                err_msg or f"Unexpected error during task {task.get_name()}",
                exc_info=exc
            )
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(_task_inner)
    return task
