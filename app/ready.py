import asyncio

from sqlalchemy import text

from app.config import get_settings
from app.db import create_engine_and_factory
from app.materials import MaterialCatalog


async def check() -> None:
    settings = get_settings()
    MaterialCatalog.load(settings.materials_dir)
    engine, session_factory = create_engine_and_factory(settings.database_url)
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
