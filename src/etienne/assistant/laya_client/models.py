"""Models used by Laya to understand which device to use"""

from typing import Literal

from pydantic import BaseModel, Field


# DEVICES
class DeviceType(BaseModel):
    device_type: Literal["light", "speaker", "tv"] = Field(
        description=(
            "Which device should handle this request? "
            "light: lighting, brightness, colours, and making rooms lighter or darker. "
            "speaker: music, songs, artists, audio playback and volume. "
            "tv: television, shows, movies, video and streaming applications."
        )
    )


class DeviceTypeDecision(BaseModel):
    device_type: Literal["speaker", "tv", "light"]
    answer_confidence: float
    decision_confidence: float
    probabilities: dict[str, float]


# Names
class DeviceNameDecision(BaseModel):
    device_name: str
    answer_confidence: float
    decision_confidence: float
    probabilities: dict[str, float]


# FINAL CLASS
class ObjectSelection(BaseModel):
    utterance: str
    device_decision: DeviceTypeDecision
    name_decision: DeviceNameDecision
