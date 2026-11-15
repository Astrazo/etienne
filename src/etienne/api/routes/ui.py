"""HTTP endpoint for the read-only device inventory."""

from fastapi import APIRouter, Request

ui_router = APIRouter(tags=["Devices"])


@ui_router.get("/api/devices")
async def devices(request: Request):
    return {"devices": request.app.state.home.get_device_inventory()}
