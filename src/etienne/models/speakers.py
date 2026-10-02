from typing import Literal

from pydantic import BaseModel


class SpeakerStatus(BaseModel):
    name: str
    spotify_id: str
    currently_playing: bool
    current_song: str | None
    current_arist: str | None
    next_song: str | None
    repeat_state: Literal["track", "context", "off"]
    shuffle_state: bool
