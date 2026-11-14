"""Models used by Ollama to understand which device to use"""

from typing import Literal, Self

from pydantic import BaseModel, Field, create_model, model_validator


class DeviceSelection(BaseModel):
    """Classify a request as device-specific, general, or needing clarification."""

    route: Literal["device", "general", "clarification"] = Field(
        description="Whether to select a device, handle a general request, or ask for clarification."
    )
    device: str | None = Field(
        description="An available device key for the device route; null otherwise."
    )
    clarification_question: str | None = Field(
        description="A question identifying the intended device for the clarification route; null otherwise."
    )

    @model_validator(mode="after")
    def validate_route(self) -> Self:
        if self.route == "device":
            if self.device is None:
                raise ValueError("The device route requires a device")
        elif self.device is not None:
            raise ValueError("Only the device route may specify a device")

        if self.route == "clarification":
            if (
                self.clarification_question is None
                or not self.clarification_question.strip()
            ):
                raise ValueError("The clarification route requires a non-empty question")
        elif self.clarification_question is not None:
            raise ValueError("Only the clarification route may specify a question")

        return self


def create_device_selection(
    device_choices: tuple[str, ...],
) -> type[DeviceSelection]:
    """Build a selection schema restricted to the currently available devices."""
    if device_choices:
        device_type = Literal[device_choices] | None
    else:
        device_type = type(None)

    return create_model(
        "DeviceSelection",
        __base__=DeviceSelection,
        device=(
            device_type,
            Field(
                description="An available device key for the device route; null otherwise."
            ),
        ),
    )
