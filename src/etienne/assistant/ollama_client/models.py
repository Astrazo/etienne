"""Models used by Ollama to understand which device to use"""

from typing import Literal

from pydantic import BaseModel, create_model


def create_device_selection(
    device_choices: tuple[str, ...],
) -> type[BaseModel]:
    device_literal = Literal[device_choices]

    return create_model(
        "DeviceSelection",
        device=(device_literal | None, ...),
    )
