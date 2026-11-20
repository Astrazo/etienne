"""Direct controls for configured individual lights and light groups."""

from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from ...devices import Light, LightGroup

lights_router = APIRouter(prefix="/lights", tags=["Lights"])


def get_light(device_key: str, request: Request) -> Light | LightGroup:
    """Accept an individual key (kitchen.devices.main) or group ID (kitchen)."""
    # Resolve configured devices instead of assuming room names or member counts.
    home = request.app.state.home
    light = home.lights.get(device_key)
    if light is None:
        light = home.light_groups.get(device_key)
    if light is None:
        raise HTTPException(404, f"Unknown light or light group: {device_key}")
    return light


LightDependency = Annotated[Light | LightGroup, Depends(get_light)]


@lights_router.post("/{device_key}/on")
async def turn_on(
    device_key: str,
    light: LightDependency,
    effect: str | None = None,
    colour: str | None = None,
    flash: Literal["short", "long"] | None = None,
):
    # Forward supported settings to the registered light or group method.
    try:
        await light.turn_on(effect=effect, colour=colour, flash=flash)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            502, "Could not turn on lights through Home Assistant"
        ) from error

    # A successful service call confirms submission, not the physical light state.
    return {"device": device_key, "action": "turn_on", "status": "submitted"}


@lights_router.post("/{device_key}/off")
async def turn_off(device_key: str, light: LightDependency):
    # Use the group method for a group, which targets all configured members.
    try:
        await light.turn_off()
    except httpx.HTTPError as error:
        raise HTTPException(
            502, "Could not turn off lights through Home Assistant"
        ) from error
    return {"device": device_key, "action": "turn_off", "status": "submitted"}


@lights_router.get("/{device_key}/state")
async def get_state(device_key: str, light: LightDependency):
    # Return full observations, including per-member states for groups.
    try:
        return await light.get_state()
    except (httpx.HTTPError, ValidationError) as error:
        raise HTTPException(
            502, "Could not read light state from Home Assistant"
        ) from error
