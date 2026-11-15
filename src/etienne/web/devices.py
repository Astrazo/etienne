"""Read-only device inventory using NiceGUI inputs and cards."""

from collections.abc import Callable

from fastapi import FastAPI
from nicegui import ui


def build_devices(api: FastAPI) -> Callable[[], None]:
    inventory = []

    @ui.refreshable
    def results():
        filtered = [
            device
            for device in inventory
            if search.value.casefold() in f"{device['name']} {device['id']}".casefold()
            and (category.value == "all" or device["type"] == category.value)
        ]
        if not filtered:
            ui.label("No matching devices.").classes("muted py-8")
            return
        ui.label(f"{len(filtered)} devices").classes("muted text-xs")
        with ui.element("div").classes("device-grid"):
            for device in filtered:
                with ui.card().classes("device-card"):
                    with ui.row().classes("w-full justify-between items-center"):
                        icon = {
                            "light": "lightbulb_outline",
                            "speaker": "speaker",
                            "tv": "tv",
                            "media_player": "tv",
                        }.get(device["type"], "devices")
                        ui.icon(icon, size="24px").classes("muted")
                        ui.label(device["state"].replace("_", " ")).classes(
                            "muted text-xs"
                        )
                    ui.label(device["name"]).classes("text-base mt-3")
                    ui.label(
                        f"{device['type'].replace('_', ' ')} · {device['source']}"
                    ).classes("muted text-xs")

    def refresh():
        nonlocal inventory
        inventory = api.state.home.get_device_inventory()
        category.set_options(
            {
                "all": "All device types",
                **{
                    kind: kind.replace("_", " ")
                    for kind in sorted({device["type"] for device in inventory})
                },
            },
            value="all",
        )
        results.refresh()

    with ui.row().classes("page-heading"):
        with ui.column().classes("gap-1"):
            ui.label("Devices").classes("page-title")
            ui.label("The things around your home.").classes("muted")
        ui.button("Refresh list", icon="refresh", on_click=refresh).props(
            "outline no-caps"
        )
    ui.label(
        "Registered Etienne devices and their last known states. Use Chat to control supported devices."
    ).classes("notice")
    with ui.row().classes("w-full items-center my-4"):
        search = (
            ui.input(placeholder="Search devices…", on_change=lambda: results.refresh())
            .props("outlined dense aria-label='Search devices'")
            .classes("device-search")
        )
        category = (
            ui.select(
                {"all": "All device types"},
                value="all",
                on_change=lambda: results.refresh(),
            )
            .props("outlined dense aria-label='Device type'")
            .classes("device-filter")
        )
    results()
    return refresh
