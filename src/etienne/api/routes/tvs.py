from fastapi import APIRouter, Request

from ...devices import TV
from ...home import Home

tv_router = APIRouter(
    prefix="/tvs",
    tags=["TVs"],
)


@tv_router.post("/{device_id}/{app}/open")
async def open_app(
    device_id: str,
    app: str,
    request: Request,
):
    home: Home = request.app.state.home
    tv: TV = home.tvs[device_id]

    await tv.open_app(app)

    return {"status": "ok"}


@tv_router.post("/{device_id}/{app}/shows/{show}/play")
async def play_show(
    device_id: str,
    app: str,
    show: str,
    request: Request,
):
    home: Home = request.app.state.home
    tv: TV = home.tvs[device_id]

    await tv.play_show(
        app=app,
        show=show,
    )

    return {"status": "ok"}
