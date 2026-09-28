from fastapi import APIRouter, Request
from ...devices import TV
from ...home import Home

tv_router = APIRouter(
    prefix="/tvs",
    tags=["TVs"],
)


@tv_router.post("/{name}/{app}/open")
async def open_app(
    name: str,
    app: str,
    request: Request,
):
    home: Home = request.app.state.home
    tv: TV = home.tvs[name]

    await tv.open_app(app)

    return {"status": "ok"}


@tv_router.post("/{name}/{app}/shows/{show}/play")
async def play_show(
    name: str,
    app: str,
    show: str,
    request: Request,
):
    home: Home = request.app.state.home
    tv: TV = home.tvs[name]

    await tv.play_show(
        app=app,
        show=show,
    )

    return {"status": "ok"}