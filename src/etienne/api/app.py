# api/app.py

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from ..assistant.laya_client import LayaClient
from ..assistant.ollama_client import OllamaClient
from ..db import init_db
from ..home import Home
from ..scheduler import run_scheduler
from ..web import register_web
from .routes import assistant_router, lights_router, speaker_router, tv_router
from .routes.ui import ui_router


def init_app(
    home: Home, laya_client: LayaClient, ollama_client: OllamaClient
) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        # Init DB and set path
        app.state.db_path = init_db()

        # Init home and laya
        await home.initialise(app.state.db_path)
        # laya_client.initialise()

        # Assign home and laya to the app state
        app.state.home = home
        app.state.laya_client = laya_client
        app.state.ollama_client = ollama_client

        # Run scheduler and set it to app state too
        scheduler = asyncio.create_task(
            run_scheduler(home, app.state.db_path), name="home-scheduler"
        )
        app.state.scheduler = scheduler

        try:
            yield
        finally:
            try:
                scheduler.cancel()
                with suppress(asyncio.CancelledError):
                    await scheduler
            finally:
                await home.close()

    app = FastAPI(lifespan=lifespan)

    app.include_router(lights_router)
    app.include_router(tv_router)
    app.include_router(speaker_router)
    app.include_router(assistant_router)
    app.include_router(ui_router)
    # NiceGUI mounts at / after the API routes so it does not shadow them.
    register_web(app)

    return app
