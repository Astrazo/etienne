"""Shared data models used by device operations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TrackInput(BaseModel):
    """A track name and its optional artist."""

    song: str
    artist: str | None = None


# Comes from Spotify
class SpeakerState(BaseModel):
    """A fresh reading of Spotify's latest known speaker state, not a local cache."""

    available: bool | None = None
    is_active: bool | None = None
    is_playing: bool | None = None

    track_uri: str | None = None
    track_name: str | None = None
    artist_name: str | None = None

    volume_percent: int | None = None
    repeat_state: Literal["off", "track", "context"] | None = None
    shuffle_state: bool | None = None

    observed_at: datetime | None = None


class LightAttributes(BaseModel):
    """Light details HA may omit when unsupported or currently unknown."""

    # Current output. Brightness uses HA's 0–255 scale.
    brightness: int | None = Field(default=None, ge=0, le=255)
    color_mode: str | None = None
    rgb_color: tuple[int, int, int] | None = None
    color_temp_kelvin: int | None = None
    effect: str | None = None

    # Capabilities used to offer appropriate controls.
    supported_color_modes: list[str] | None = None
    min_color_temp_kelvin: int | None = None
    max_color_temp_kelvin: int | None = None
    effect_list: list[str] | None = None


# Comes from HA
class LightState(BaseModel):
    """HA's latest known Light state"""

    state: Literal["on", "off", "unknown", "unavailable"]
    entity_id: str | None = None
    attributes: LightAttributes = Field(default_factory=LightAttributes)

    # HA timestamps, not the time Etienne fetched this response.
    last_changed: datetime | None = None
    last_updated: datetime | None = None
    last_reported: datetime | None = None


class TvAttributes(BaseModel):
    """TV details reported by its HA integration; unsupported fields stay absent."""

    app_id: str | None = None
    app_name: str | None = None
    media_title: str | None = None
    source: str | None = None
    volume_level: float | None = Field(default=None, ge=0, le=1)
    is_volume_muted: bool | None = None

# Comes from HA
class TvState(BaseModel):
    """HA's latest known TV state"""

    state: Literal[
        "on",
        "off",
        "idle",
        "standby",
        "playing",
        "paused",
        "buffering",
        "unknown",
        "unavailable",
    ]
    entity_id: str | None = None
    attributes: TvAttributes = Field(default_factory=TvAttributes)

    # HA timestamps, not the time Etienne fetched this response.
    last_changed: datetime | None = None
    last_updated: datetime | None = None
    last_reported: datetime | None = None
