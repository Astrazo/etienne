import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Self

from fastapi import APIRouter, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, Field, model_validator
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

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

    tracks = [(track.song, track.artist) for track in tracks_input]

    try:
        await speaker.play_tracks(tracks)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play tracks through Spotify",
        ) from error

    return {"speaker": name, "action": "play_tracks", "status": "completed"}


@speaker_router.post("/{name}/play/album")
async def play_album(
    name: str,
    album: str,
    artist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.play_album(album_name=album, artist_name=artist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the album through Spotify",
        ) from error

    return {"speaker": name, "action": "play_album", "status": "completed"}


@speaker_router.post("/{name}/play/artist")
async def play_artist(
    name: str,
    artist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.play_artist(artist_name=artist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the artist through Spotify",
        ) from error

    return {"speaker": name, "action": "play_artist", "status": "completed"}


@speaker_router.post("/{name}/play/playlist")
async def play_playlist(
    name: str,
    playlist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.play_playlist(playlist_name=playlist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the playlist through Spotify",
        ) from error

    return {"speaker": name, "action": "play_playlist", "status": "completed"}


@speaker_router.post("/{name}/pause")
async def pause(
    name: str,
    request: Request,
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.pause()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not pause playback through Spotify",
        ) from error

    return {"speaker": name, "action": "pause", "status": "completed"}


@speaker_router.post("/{name}/resume")
async def resume(name: str, request: Request):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]

    try:
        await speaker.resume()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not resume playback through Spotify",
        ) from error

    return {"speaker": name, "action": "resume", "status": "completed"}


@speaker_router.post("/{name}/repeat")
async def repeat(
    name: str,
    request: Request,
    state: Literal["track", "context", "off"],
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.repeat(state=state)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not set repeat through Spotify",
        ) from error

    return {"speaker": name, "action": "repeat", "status": "completed", "state": state}


@speaker_router.post("/{name}/shuffle")
async def shuffle(name: str, request: Request, state: bool):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.shuffle(state=state)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not set shuffle through Spotify",
        ) from error

    return {"speaker": name, "action": "shuffle", "status": "completed", "state": state}


@speaker_router.post("/{name}/queue/add")
async def add_to_playback_queue(name: str, request: Request, track_uri: str):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.add_to_playback_queue(track_uri)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not add the track to the Spotify queue",
        ) from error

    return {
        "speaker": name,
        "action": "add_to_playback_queue",
        "status": "completed",
        "track_uri": track_uri,
    }


@speaker_router.post("/{name}/queue/navigate")
async def navigate_queue(
    name: str, request: Request, direction: Literal["next", "previous"]
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    try:
        await speaker.navigate_queue(direction)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not navigate the Spotify queue",
        ) from error

    return {
        "speaker": name,
        "action": "navigate_queue",
        "status": "completed",
        "direction": direction,
    }


class SleepTimerInput(BaseModel):
    duration_hr: int | None = Field(default=None, gt=0)
    off_time: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_choice(self) -> Self:
        if (self.duration_hr is not None and self.off_time is not None) or (
            self.duration_hr is None and self.off_time is None
        ):
            raise ValueError("Provide exactly one duration_hr or off_time argument")

        if self.off_time is not None and self.off_time <= datetime.now(UTC):
            raise ValueError("off_time must be in the future")

        return self


@speaker_router.post("/{name}/sleep_timer")
async def set_sleep_timer(name: str, request: Request, timer: SleepTimerInput):

    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]
    db_path: Path = request.app.state.db_path

    # Determine time
    if timer.duration_hr is not None:
        sleep_time = datetime.now(UTC) + timedelta(hours=timer.duration_hr)
    elif timer.off_time is not None:
        sleep_time = timer.off_time.astimezone(UTC)

    try:
        await speaker.set_sleep_timer(sleep_time, db_path)
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the sleep timer",
        ) from error

    return {
        "speaker": name,
        "action": "set_sleep_timer",
        "status": "scheduled",
        "sleep_time": sleep_time,
    }


"""@speaker_router.get("/{name}/status")
async def get_playback(name: str, request: Request):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[name]

    playback = speaker.get_playback()

    return playback"""
