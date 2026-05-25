from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine
from app.logging import configure_logging, get_logger

log = get_logger(__name__)


async def init_db(drop: bool = False) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    log.info("db.init.done", drop=drop)


if __name__ == "__main__":
    import sys

    configure_logging()
    asyncio.run(init_db(drop="--drop" in sys.argv))
