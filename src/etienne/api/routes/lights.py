from fastapi import APIRouter, Request

from ...devices import Light

lights_router = APIRouter(
    prefix="/lights",
    tags=["Lights"],
)


@lights_router.post("/{name}/on")
async def turn_on(
    name: str,
    request: Request,
):
    # Use the request object to access home object
    home = request.app.state.home

    # TODO We need to determine between individual lights and rooms
    if name == "living_room":
        for i in range(1, 4):
            # Grab the light and turn it on
            light = home.lights[f"{name}_{i}"]
            await light.turn_on()
    else:
        # Grab the light and turn it on
        light: Light = home.lights[name]
        await light.turn_on()

    # We always work
    return {"status": "ok"}


@lights_router.post("/{name}/off")
async def turn_off(
    name: str,
    request: Request,
):
    # Use the request object to access home object
    home = request.app.state.home

    # TODO We need to determine between individual lights and rooms
    if name == "living_room":
        for i in range(1, 4):
            # Grab the light and turn it on
            light = home.lights[f"{name}_{i}"]
            await light.turn_off()
    else:
        # Grab the light and turn it on
        light: Light = home.lights[name]
        await light.turn_off()

    # We always work
    return {"status": "ok"}
