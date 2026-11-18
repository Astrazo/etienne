from fastapi import APIRouter, Request

from ...devices import Light

lights_router = APIRouter(
    prefix="/lights",
    tags=["Lights"],
)


@lights_router.post("/{device_key}/on")
async def turn_on(
    device_key: str,
    request: Request,
):
    # Use the request object to access home object
    home = request.app.state.home

    # TODO We need to determine between individual lights and rooms
    if device_key == "living_room":
        for i in range(1, 4):
            # Grab the light and turn it on
            light = home.lights[f"{device_key}_{i}"]
            await light.turn_on()
    else:
        # Grab the light and turn it on
        light: Light = home.lights[device_key]
        await light.turn_on()

    # We always work
    return {"status": "ok"}


@lights_router.post("/{device_key}/off")
async def turn_off(
    device_key: str,
    request: Request,
):
    # Use the request object to access home object
    home = request.app.state.home

    # TODO We need to determine between individual lights and rooms
    if device_key == "living_room":
        for i in range(1, 4):
            # Grab the light and turn it on
            light = home.lights[f"{device_key}_{i}"]
            await light.turn_off()
    else:
        # Grab the light and turn it on
        light: Light = home.lights[device_key]
        await light.turn_off()

    # We always work
    return {"status": "ok"}
