# api/app.py

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..home import Home
from .routes import lights_router, tv_router, speaker_router


def init_app(home: Home) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):

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