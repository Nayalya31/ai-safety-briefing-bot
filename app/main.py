import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher

from app.bot.handlers import router
from app.bot.middleware import DatabaseMiddleware
from app.config import get_settings
from app.db import create_engine_and_factory
from app.health import create_health_app
from app.materials import MaterialCatalog
from app.services import AIExplainer, TrainingService


async def run() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    catalog = MaterialCatalog.load(settings.materials_dir)
    engine, session_factory = create_engine_and_factory(settings.database_url)
    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.update.outer_middleware(DatabaseMiddleware(session_factory))
    dispatcher.include_router(router)
    dispatcher["catalog"] = catalog
    dispatcher["training_service"] = TrainingService()
    ai_explainer = AIExplainer(settings.openai_api_key, settings.openai_model)
    dispatcher["ai_explainer"] = ai_explainer

    runner = web.AppRunner(create_health_app(session_factory))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", settings.health_port).start()
    try:
        await dispatcher.start_polling(bot)
    finally:
        await runner.cleanup()
        await ai_explainer.close()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
