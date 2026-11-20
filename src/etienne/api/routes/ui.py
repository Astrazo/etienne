"""Read-only device inventory and live observations for debugging."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request

ui_router = APIRouter(tags=["Devices"])


@ui_router.get("/api/devices")
async def devices(request: Request):
    return {"devices": await request.app.state.home.get_device_display_data()}


@ui_router.get("/api/state")
async def home_state(
    request: Request,
    device_types: Annotated[
        list[Literal["speakers", "lights", "tvs"]] | None, Query()
    ] = None,
):
    # Filter at the source so debugging lights does not also contact Spotify or TVs.
    selected_types = None
    if device_types is not None:
        selected_types = set(device_types)
    return await request.app.state.home.get_home_state(device_types=selected_types)
