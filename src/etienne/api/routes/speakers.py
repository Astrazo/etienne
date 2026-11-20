import sqlite3
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, Field, model_validator
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from ...devices import Speaker, TrackInput
from ...home import Home

speaker_router = APIRouter(
    prefix="/speakers",
    tags=["Speakers"],
)


def get_speaker(device_id: str, request: Request) -> Speaker:
    # Resolve configured IDs before calling a device method.
    home: Home = request.app.state.home
    speaker = home.speakers.get(device_id)
    if speaker is None:
        raise HTTPException(404, f"Unknown speaker: {device_id}")
    return speaker


SpeakerDependency = Annotated[Speaker, Depends(get_speaker)]


@speaker_router.post("/{device_id}/play/tracks")
async def play_tracks(
    device_id: str,
    tracks_input: list[TrackInput],
    speaker: SpeakerDependency,
):
    # Play the requested tracks and retain partial-match messages.
    try:
        result = await speaker.play_tracks(tracks_input)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play tracks through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "play_tracks",
        "status": "completed",
        "result": result,
        "tracks": tracks_input,
    }


@speaker_router.post("/{device_id}/play/album")
async def play_album(
    device_id: str,
    album: str,
    speaker: SpeakerDependency,
    artist: str | None = None,
):
    # Search for the album, optionally restricting it to an artist.
    try:
        result = await speaker.play_album(album_name=album, artist_name=artist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the album through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "play_album",
        "status": "completed",
        "result": result,
    }


@speaker_router.post("/{device_id}/play/artist")
async def play_artist(
    device_id: str,
    artist: str,
    speaker: SpeakerDependency,
):
    # Search for the artist and request playback.
    try:
        result = await speaker.play_artist(artist_name=artist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the artist through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "play_artist",
        "status": "completed",
        "result": result,
    }


@speaker_router.post("/{device_id}/play/playlist")
async def play_playlist(
    device_id: str,
    playlist: str,
    speaker: SpeakerDependency,
):
    # Search for the playlist and request playback.
    try:
        result = await speaker.play_playlist(playlist_name=playlist)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not play the playlist through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "play_playlist",
        "status": "completed",
        "result": result,
    }


@speaker_router.post("/{device_id}/pause")
async def pause(
    device_id: str,
    speaker: SpeakerDependency,
):
    # Pause playback on the configured speaker.
    try:
        result = await speaker.pause()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not pause playback through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "pause",
        "status": "completed",
        "result": result,
    }


@speaker_router.post("/{device_id}/resume")
async def resume(device_id: str, speaker: SpeakerDependency):
    # Resume playback on the configured speaker.
    try:
        result = await speaker.resume()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not resume playback through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "resume",
        "status": "completed",
        "result": result,
    }


@speaker_router.post("/{device_id}/repeat")
async def repeat(
    device_id: str,
    speaker: SpeakerDependency,
    state: Literal["track", "context", "off"],
):
    # Set the requested Spotify repeat mode.
    try:
        result = await speaker.repeat(state=state)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not set repeat through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "repeat",
        "status": "completed",
        "result": result,
        "state": state,
    }


@speaker_router.post("/{device_id}/shuffle")
async def shuffle(device_id: str, speaker: SpeakerDependency, state: bool):
    # Set the requested Spotify shuffle mode.
    try:
        result = await speaker.shuffle(state=state)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not set shuffle through Spotify",
        ) from error

    return {
        "speaker": device_id,
        "action": "shuffle",
        "status": "completed",
        "result": result,
        "state": state,
    }


@speaker_router.post("/{device_id}/queue/add")
async def add_to_playback_queue(
    device_id: str, speaker: SpeakerDependency, tracks_input: list[TrackInput]
):
    # Add matching tracks and retain any missing-track details.
    try:
        result = await speaker.add_to_playback_queue(tracks_input)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not add the track to the Spotify queue",
        ) from error

    return {
        "speaker": device_id,
        "action": "add_to_playback_queue",
        "status": "completed",
        "result": result,
        "tracks": tracks_input,
    }


@speaker_router.post("/{device_id}/queue/navigate")
async def navigate_queue(
    device_id: str, speaker: SpeakerDependency, direction: Literal["next", "previous"]
):
    # Move through the playback queue in the requested direction.
    try:
        result = await speaker.navigate_queue(direction)
    except (SpotifyException, RequestException) as error:
        raise HTTPException(
            status_code=502,
            detail="Could not navigate the Spotify queue",
        ) from error

    return {
        "speaker": device_id,
        "action": "navigate_queue",
        "status": "completed",
        "result": result,
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
async def set_timer(device_id: str, speaker: SpeakerDependency, timer: TimerInput):
    # Save the timer and return the device method's scheduling message.
    try:
        result = await speaker.set_timer(
            action=timer.action,
            timer_minutes=timer.timer_minutes,
            trigger_time=timer.trigger_time,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the sleep timer",
        ) from error

    return {
        "speaker": device_id,
        "message": result,
        "status": "scheduled",
        "timer": timer,
    }


@speaker_router.get("/{device_id}/status", include_in_schema=False)
@speaker_router.get("/{device_id}/state")
async def get_state(device_id: str, speaker: SpeakerDependency):
    # Read fresh Spotify state rather than keeping a route-level cache.
    try:
        return await speaker.get_state()
    except (SpotifyException, RequestException) as error:
        raise HTTPException(502, "Could not read Spotify playback state") from error


@speaker_router.get("/{device_id}/timers")
async def get_timers(
    device_id: str,
    speaker: SpeakerDependency,
    action: Literal["resume", "pause"] | None = None,
    trigger_time: AwareDatetime | None = None,
):
    # Forward optional filters to the same method used by the assistant.
    try:
        result = await speaker.get_timers(action=action, trigger_time=trigger_time)
    except sqlite3.Error as error:
        raise HTTPException(500, "Could not read speaker timers") from error
    return {"speaker": device_id, "result": result}


@speaker_router.delete("/{device_id}/timers")
async def cancel_timer(
    device_id: str,
    speaker: SpeakerDependency,
    action: Literal["resume", "pause"] | None = None,
    trigger_time: AwareDatetime | None = None,
    cancel_all: bool = False,
):
    # Preserve the device method's ambiguity handling when several timers match.
    try:
        result = await speaker.cancel_timer(
            action=action, trigger_time=trigger_time, cancel_all=cancel_all
        )
    except sqlite3.Error as error:
        raise HTTPException(500, "Could not cancel speaker timers") from error
    return {"speaker": device_id, "result": result}
