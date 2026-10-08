from .assistant import assistant_router
from .lights import lights_router
from .speakers import TrackInput, speaker_router
from .tvs import tv_router

__all__ = [
    "TrackInput",
    "assistant_router",
    "lights_router",
    "speaker_router",
    "tv_router",
]
