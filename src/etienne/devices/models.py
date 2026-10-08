"""Shared data models used by device operations."""

from pydantic import BaseModel


class TrackInput(BaseModel):
    """A track name and its optional artist."""

    song: str
    artist: str | None = None
