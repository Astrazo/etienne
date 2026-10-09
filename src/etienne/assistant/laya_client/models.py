"""Models used by Laya to understand which device to use"""

from typing import Literal

from pydantic import BaseModel, Field


# DEVICES
class DeviceType(BaseModel):
    device_type: Literal["lights", "speakers", "tvs"] = Field(
        description=(
            "Which device should handle this request? "
            "lights: lighting, brightness, colours, and making rooms lighter or darker. "
            "speakers: music, songs, artists, audio playback and volume. "
            "tvs: television, shows, movies, video and streaming applications."
        )
    )


class DeviceTypeDecision(BaseModel):
    device_type: Literal["speakers", "tvs", "lights"]
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
