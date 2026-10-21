"""Load local device configuration from TOML."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TVConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1)
    port: int = Field(default=5555, ge=1, le=65535)


class HomeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_assistant_url: str = "http://homeassistant.local"
    lights: dict[str, str] = Field(default_factory=dict)
    speakers: dict[str, str] = Field(default_factory=dict)
    tvs: dict[str, TVConfig] = Field(default_factory=dict)


def load_config(path: Path = Path("config.toml")) -> HomeConfig:
    """Read configuration relative to the working directory by default."""
    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Missing {path}. Copy config.example.toml to {path} "
            "and fill in your device details."
        ) from None

    return HomeConfig.model_validate(data)
