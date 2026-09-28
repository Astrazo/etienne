from fastapi import APIRouter, Request
from ...devices import Speaker
from ...home import Home

speaker_router = APIRouter(
    prefix="/speakers",
    tags=["Speakers"],
)


@speaker_router.post("/{name}/play")
async def play(
    name: str,
    request: Request,
    song: str | None = None,
    artist: str | None = None,
):
    home: Home = request.app.state.home
    speaker = home.speakers[name]
    speaker.play(
        song=song,
        artist=artist,
    )

    return {"status": "ok"}

@speaker_router.post("/{name}/pause")
async def pause(
    name: str,
    request: Request,
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    speaker.pause()

    # We always work 
    return {"status": "ok"}