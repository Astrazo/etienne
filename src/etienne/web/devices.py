"""Registered devices with direct power switches and saved light settings."""

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from functools import partial

import httpx
import webcolors
from fastapi import FastAPI
from loguru import logger
from nicegui import ui
from pydantic import ValidationError

from ..devices import Light
from ..devices.models import LightState

STATE_CONFIRMATION_TIMEOUT = 5.0
STATE_POLL_INTERVAL = 0.25


def build_devices(
    api: FastAPI, storage: MutableMapping
) -> Callable[[], Awaitable[None]]:
    inventory = []
    selected_id: str | None = None
    loading_settings = False
    pending_power = {}
    error_status = {}

    async def open_settings(device_id: str):
        nonlocal selected_id, loading_settings
        if loading_settings:
            return
        light = api.state.home.get_device_map().get(device_id)
        if not isinstance(light, Light):
            ui.notify("This light is no longer registered.", type="warning")
            return
        selected_id = device_id
        options = storage.get("light_settings", {}).get(device_id, {})
        heading.text = f"{light.name.replace('_', ' ').title()} settings"
        colour.value = options.get("colour") or ""
        effect.value = options.get("effect") or ""
        effect.set_autocomplete([])
        flash.value = options.get("flash") or ""
        settings_status.text = "Loading available effects…"
        editor.open()
        loading_settings = True
        save_button.disable()
        try:
            async with asyncio.timeout(15):
                snapshot = await light.get_state()
            effects = snapshot.attributes.effect_list or []
            effect.set_autocomplete(effects)
            settings_status.text = ""
            show_light_observation(device_id, snapshot)
        except httpx.HTTPError, TimeoutError, ValidationError:
            settings_status.text = (
                "Couldn’t load available effects. You can still save settings."
            )
        finally:
            loading_settings = False
            save_button.enable()

    def save_settings():
        if selected_id is None or loading_settings:
            return
        options = {
            "colour": (colour.value or "").strip() or None,
            "effect": (effect.value or "").strip() or None,
            "flash": flash.value or None,
        }
        try:
            if options["colour"] is not None:
                webcolors.name_to_rgb(options["colour"])
            if options["flash"] not in (None, "short", "long"):
                raise ValueError("Invalid flash option")
        except ValueError:
            settings_status.text = "Check the colour name and flash option."
            return
        settings = dict(storage.get("light_settings", {}))
        settings[selected_id] = options
        storage["light_settings"] = settings
        editor.close()
        ui.notify("Light settings saved. They’ll apply next time you switch it on.")

    async def toggle_light(device_id: str, event):
        if device_id in pending_power:
            return
        light = api.state.home.get_device_map().get(device_id)
        if not isinstance(light, Light):
            ui.notify("This light is no longer registered.", type="warning")
            results.refresh()
            return
        turn_on = event.value
        options = dict(storage.get("light_settings", {}).get(device_id, {}))
        error_status.pop(device_id, None)
        pending_power[device_id] = turn_on
        event.sender.disable()
        results.refresh()
        observation = None
        try:
            async with asyncio.timeout(15):
                if turn_on:
                    await light.turn_on(
                        colour=options.get("colour"),
                        effect=options.get("effect"),
                        flash=options.get("flash"),
                    )
                else:
                    await light.turn_off()
        except ValueError:
            error_status[device_id] = (
                "Check this light’s saved settings. No command was sent."
            )
        except httpx.HTTPError, TimeoutError:
            error_status[device_id] = (
                "Couldn’t confirm the command. Check the light before trying again."
            )
        except Exception:  # noqa: BLE001 - report unexpected control failures in the UI
            logger.exception("Light control failed for {}", light.name)
            error_status[device_id] = (
                "The command failed. Check the server logs and the light."
            )
        else:
            try:
                # HA may accept the service call before publishing the new state.
                # Poll observations only: never resend an effect or power command.
                async with asyncio.timeout(STATE_CONFIRMATION_TIMEOUT):
                    while True:
                        observation = await light.get_state()
                        if observation.state == ("on" if turn_on else "off"):
                            break
                        await asyncio.sleep(STATE_POLL_INTERVAL)
            except TimeoutError:
                error_status[device_id] = (
                    "Command sent, but the requested state hasn’t been confirmed yet."
                )
            except httpx.HTTPError, ValidationError:
                observation = LightState(state="unavailable")
                error_status[device_id] = (
                    "Command sent, but the state couldn’t be refreshed."
                )
        finally:
            pending_power.pop(device_id, None)
            if observation is not None:
                show_light_observation(device_id, observation)
            else:
                results.refresh()

    def show_light_observation(device_id: str, observation: LightState):
        # Only update this page's rendered observation, never the device object.
        for entry in inventory:
            if entry["id"] == device_id:
                entry["state"] = observation.state
                entry.pop("error", None)
                break
        results.refresh()

    with ui.dialog() as editor, ui.card().classes("light-editor"):
        with ui.row().classes("w-full justify-between items-center"):
            heading = ui.label().classes("text-xl")
            ui.button(icon="close", on_click=editor.close).props(
                "flat round aria-label=Close"
            )
        settings_status = ui.label().classes("muted text-sm").props("role=status")
        colour = (
            ui.input("Colour (optional)", placeholder="e.g. red or blue")
            .props("outlined maxlength=50")
            .classes("w-full")
        )
        effect = (
            ui.input("Effect (optional)", autocomplete=[])
            .props("outlined maxlength=100")
            .classes("w-full")
        )
        ui.label(
            "Used when you switch this light on. Leave blank to keep the light’s current settings. Saving doesn’t change its power."
        ).classes("muted text-xs")
        flash = (
            ui.select(
                {"": "No flash", "short": "Short flash", "long": "Long flash"},
                value="",
                label="Flash",
            )
            .props("outlined")
            .classes("w-full")
        )
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=editor.close).props("flat no-caps")
            save_button = ui.button("Save settings", on_click=save_settings).props(
                "unelevated no-caps text-color=black"
            )

    @ui.refreshable
    def results():
        filtered = [
            device
            for device in inventory
            if search.value.casefold() in f"{device['name']} {device['id']}".casefold()
        ]
        if not filtered:
            ui.label("No matching devices.").classes("muted py-8")
            return
        ui.label(f"{len(filtered)} devices").classes("muted text-xs")
        for device_type, title in (
            ("light", "Lights"),
            ("speaker", "Speakers"),
            ("tv", "TVs"),
        ):
            devices = sorted(
                (device for device in filtered if device["type"] == device_type),
                key=lambda device: (device["name"].casefold(), device["id"]),
            )
            if not devices:
                continue
            with ui.element("section").classes("w-full mb-6"):
                with ui.row().classes("items-center gap-2 mt-4 mb-3"):
                    ui.label(title).classes("text-lg").props(
                        "role=heading aria-level=2"
                    )
                    ui.label(str(len(devices))).classes("muted text-xs")
                with ui.element("div").classes("device-grid"):
                    for device in devices:
                        with ui.card().classes("device-card"):
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
                                icon = {
                                    "light": "lightbulb_outline",
                                    "speaker": "speaker",
                                    "tv": "tv",
                                    "media_player": "tv",
                                }.get(device["type"], "devices")
                                ui.icon(icon, size="24px").classes("muted")
                                ui.label(device["state"].replace("_", " ")).classes(
                                    "muted text-xs"
                                ).mark(f"device-state-{device['id']}")
                            ui.label(device["name"]).classes("text-base mt-3")
                            ui.label(
                                f"{device['type'].replace('_', ' ')} · {device['source']}"
                            ).classes("muted text-xs")
                            if device["type"] == "light":
                                with ui.row().classes(
                                    "w-full justify-between items-center mt-2"
                                ):
                                    power = ui.switch(
                                        "Power",
                                        value=pending_power.get(
                                            device["id"], device["state"] == "on"
                                        ),
                                        on_change=partial(toggle_light, device["id"]),
                                    ).mark(f"power-{device['id']}")
                                    if device["id"] in pending_power:
                                        power.disable()
                                    ui.button(
                                        icon="settings",
                                        on_click=partial(open_settings, device["id"]),
                                    ).props(
                                        "flat round aria-label='Light settings'"
                                    ).tooltip("Light settings").mark(
                                        f"settings-{device['id']}"
                                    )
                                message = error_status.get(device["id"]) or device.get(
                                    "error"
                                )
                                if message:
                                    ui.label(message).classes("error text-xs").props(
                                        "role=alert"
                                    ).mark(f"light-error-{device['id']}")

    async def refresh():
        nonlocal inventory
        refresh_button.disable()
        loading.text = "Reading current device states…"
        try:
            inventory = await api.state.home.get_device_inventory()
            results.refresh()
        finally:
            loading.text = ""
            refresh_button.enable()

    with ui.row().classes("page-heading"):
        with ui.column().classes("gap-1"):
            ui.label("Devices").classes("page-title")
            ui.label("The things around your home.").classes("muted")
        refresh_button = ui.button(
            "Refresh states", icon="refresh", on_click=refresh
        ).props("outline no-caps")
    ui.label(
        "Registered devices with freshly requested states. Use the switch for power and the gear for turn-on settings."
    ).classes("notice")
    with ui.row().classes("w-full items-center my-4"):
        search = (
            ui.input(placeholder="Search devices…", on_change=lambda: results.refresh())
            .props("outlined dense aria-label='Search devices'")
            .classes("device-search")
        )
    loading = ui.label().classes("muted text-xs").props("role=status")
    results()
    return refresh
