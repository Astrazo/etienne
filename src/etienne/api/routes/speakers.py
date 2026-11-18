import sqlite3
from datetime import UTC, datetime
from typing import Literal, Self

from fastapi import APIRouter, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, Field, model_validator
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from ...devices import Speaker, TrackInput
from ...home import Home

speaker_router = APIRouter(
    prefix="/speakers",
    tags=["Speakers"],
)


@speaker_router.post("/{device_id}/play/tracks")
async def play_tracks(
    device_id: str,
    tracks_input: list[TrackInput],
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]

    try:
        await speaker.play_tracks(tracks_input)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play tracks through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "play_tracks",
        "status": "completed",
        "tracks": tracks_input,
    }


@speaker_router.post("/{device_id}/play/album")
async def play_album(
    device_id: str,
    album: str,
    artist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.play_album(album_name=album, artist_name=artist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the album through Spotify",
        ) from error

    return {"speaker": device_id, "action": "play_album", "status": "completed"}


@speaker_router.post("/{device_id}/play/artist")
async def play_artist(
    device_id: str,
    artist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.play_artist(artist_name=artist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the artist through Spotify",
        ) from error

    return {"speaker": device_id, "action": "play_artist", "status": "completed"}


@speaker_router.post("/{device_id}/play/playlist")
async def play_playlist(
    device_id: str,
    playlist: str,
    request: Request,
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.play_playlist(playlist_name=playlist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the playlist through Spotify",
        ) from error

    return {"speaker": device_id, "action": "play_playlist", "status": "completed"}


@speaker_router.post("/{device_id}/pause")
async def pause(
    device_id: str,
    request: Request,
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.pause()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not pause playback through Spotify",
        ) from error

    return {"speaker": device_id, "action": "pause", "status": "completed"}


@speaker_router.post("/{device_id}/resume")
async def resume(device_id: str, request: Request):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]

    try:
        await speaker.resume()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not resume playback through Spotify",
        ) from error

    return {"speaker": device_id, "action": "resume", "status": "completed"}


@speaker_router.post("/{device_id}/repeat")
async def repeat(
    device_id: str,
    request: Request,
    state: Literal["track", "context", "off"],
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.repeat(state=state)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not set repeat through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "repeat",
        "status": "completed",
        "state": state,
    }


@speaker_router.post("/{device_id}/shuffle")
async def shuffle(device_id: str, request: Request, state: bool):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.shuffle(state=state)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not set shuffle through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "shuffle",
        "status": "completed",
        "state": state,
    }


@speaker_router.post("/{device_id}/queue/add")
async def add_to_playback_queue(
    device_id: str, request: Request, tracks_input: list[TrackInput]
):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.add_to_playback_queue(tracks_input)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not add the track to the Spotify queue",
        ) from error

    return {
        "speaker": device_id,
        "action": "add_to_playback_queue",
        "status": "completed",
        "tracks": tracks_input,
    }


@speaker_router.post("/{device_id}/queue/navigate")
async def navigate_queue(
    device_id: str, request: Request, direction: Literal["next", "previous"]
):
    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.navigate_queue(direction)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not navigate the Spotify queue",
        ) from error

    return {
        "speaker": device_id,
        "action": "navigate_queue",
        "status": "completed",
        "direction": direction,
    }


class TimerInput(BaseModel):
    action: Literal["resume", "pause"]
    timer_minutes: float | None = Field(default=None, gt=0)
    trigger_time: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_choice(self) -> Self:
        if (self.timer_minutes is not None and self.trigger_time is not None) or (
            self.timer_minutes is None and self.trigger_time is None
        ):
            raise ValueError("Provide exactly one of timer_minutes or trigger_time")

        if self.trigger_time is not None and self.trigger_time <= datetime.now(UTC):
            raise ValueError("trigger_time must be in the future")

        return self


@speaker_router.post("/{device_id}/timer")
async def set_timer(device_id: str, request: Request, timer: TimerInput):

    # Use the request object to access home object
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]
    try:
        await speaker.set_timer(
            action=timer.action,
            timer_minutes=timer.timer_minutes,
            trigger_time=timer.trigger_time,
        )
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the sleep timer",
        ) from error

    return {
        "speaker": device_id,
        "message": f"set_{timer.action}_timer",
        "status": "scheduled",
        "trigger_time": timer,
    }


"""@speaker_router.get("/{device_id}/status")
async def get_playback(device_id: str, request: Request):
    home: Home = request.app.state.home
    speaker: Speaker = home.speakers[device_id]

    playback = speaker.get_playback()

    return playback"""
