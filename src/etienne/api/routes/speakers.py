from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ...devices import Speaker
from ...home import Home

speaker_router = APIRouter(
    prefix="/speakers",
    tags=["Speakers"],
)

class TrackInput(BaseModel):
    song: str
    artist: str | None = None


@speaker_router.post("/{name}/play/tracks")
async def play_tracks(
    name: str,
    tracks_input: list[TrackInput],
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    
    tracks = [
        (track.song, track.artist)
        for track in tracks_input
    ]

    speaker.play_tracks(tracks)

    return {"status": "ok"}

@speaker_router.post("/{name}/play/album")
async def play_album(
    name: str,
    album: str,
    arist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    speaker.play_album(album_name=album, artist_name=arist)

    return {"status": "ok"}

@speaker_router.post("/{name}/play/artist")
async def play_artist(
    name: str,
    arist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    speaker.play_artist(album_name=arist)

    return {"status": "ok"}

@speaker_router.post("/{name}/play/playlist")
async def play_playlist(
    name: str,
    playlist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    speaker.play_playlist(playlist_name=playlist)

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


@speaker_router.post("/{name}/repeat")
async def repeat(
    name: str,
    request: Request,
    state: Literal["track", "context", "off"],
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    speaker.repeat(state=state)

    # We always work
    return {"status": "ok"}


@speaker_router.post("/{name}/shuffle")
async def shuffle(name: str, request: Request, state: bool):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    speaker.shuffle(state=state)

    # We always work
    return {"status": "ok"}
