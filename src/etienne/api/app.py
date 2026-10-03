# api/app.py

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from ..db import init_db
from ..home import Home
from ..scheduler import run_scheduler
from .routes import lights_router, speaker_router, tv_router


def init_app(home: Home) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        # Init DB and set path
        app.state.db_path = init_db()

        # Init home
        await home.initialise()

        # Assign it to the app state
        app.state.home = home

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

    return app
