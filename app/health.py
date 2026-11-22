from aiohttp import web
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker


def create_health_app(session_factory: async_sessionmaker) -> web.Application:
    app = web.Application()

    async def live(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def ready(_: web.Request) -> web.Response:
        try:
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
            return web.json_response({"status": "ready"})
        except Exception:
            return web.json_response({"status": "not_ready"}, status=503)

    app.router.add_get("/healthz", live)
    app.router.add_get("/readyz", ready)
    return app
