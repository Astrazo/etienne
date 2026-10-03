# api/app.py

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..db import init_db
from ..home import Home
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

        yield

        await home.close()

    app = FastAPI(lifespan=lifespan)

    app.include_router(lights_router)
    app.include_router(tv_router)
    app.include_router(speaker_router)

    return app
