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
    selected_device_key: str | None = None
    loading_settings = False
    pending_power = {}
    error_status = {}
    expanded_groups = {}
    pending_groups = {}
    group_errors = {}

    async def open_settings(device_key: str):
        nonlocal selected_device_key, loading_settings
        if loading_settings:
            return
        light = api.state.home.get_device_map().get(device_key)
        if not isinstance(light, Light):
            ui.notify("This light is no longer registered.", type="warning")
            return
        selected_device_key = device_key
        options = storage.get("light_settings", {}).get(device_key, {})
        heading.text = f"{light.display_name} settings"
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
            show_light_observation(device_key, snapshot)
        except httpx.HTTPError, TimeoutError, ValidationError:
            settings_status.text = (
                "Couldn’t load available effects. You can still save settings."
            )
        finally:
            loading_settings = False
            save_button.enable()

    def save_settings():
        if selected_device_key is None or loading_settings:
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
        settings[selected_device_key] = options
        storage["light_settings"] = settings
        editor.close()
        ui.notify("Light settings saved. They’ll apply next time you switch it on.")

    async def set_light_power(device_key: str, turn_on: bool):
        if device_key in pending_power:
            return
        light = api.state.home.get_device_map().get(device_key)
        if not isinstance(light, Light):
            ui.notify("This light is no longer registered.", type="warning")
            results.refresh()
            return
        options = dict(storage.get("light_settings", {}).get(device_key, {}))
        error_status.pop(device_key, None)
        pending_power[device_key] = turn_on
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
            error_status[device_key] = (
                "Check this light’s saved settings. No command was sent."
            )
        except httpx.HTTPError, TimeoutError:
            error_status[device_key] = (
                "Couldn’t confirm the command. Check the light before trying again."
            )
        except Exception:  # noqa: BLE001 - report unexpected control failures in the UI
            logger.exception("Light control failed for {}", device_key)
            error_status[device_key] = (
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
                error_status[device_key] = (
                    "Command sent, but the requested state hasn’t been confirmed yet."
                )
            except httpx.HTTPError, ValidationError:
                observation = LightState(state="unavailable")
                error_status[device_key] = (
                    "Command sent, but the state couldn’t be refreshed."
                )
        finally:
            pending_power.pop(device_key, None)
            if observation is not None:
                show_light_observation(device_key, observation)
            else:
                results.refresh()

    def show_light_observation(device_key: str, observation: LightState):
        # Only update this page's rendered observation, never the device object.
        for entry in inventory:
            if entry["id"] == device_key:
                entry["state"] = observation.state
                entry.pop("error", None)
                break
        results.refresh()

    async def set_light_group_power(group_id: str, turn_on: bool):
        group = api.state.home.light_groups.get(group_id)
        if group is None or not group.devices or group_id in pending_groups:
            return

        device_keys = []
        for device_id in group.devices:
            device_key = f"lights:{group_id}.devices.{device_id}"
            if device_key in pending_power:
                return
            device_keys.append(device_key)

        # Lock member tiles while the group command is being confirmed.
        pending_groups[group_id] = turn_on
        group_errors.pop(group_id, None)
        for device_key in device_keys:
            pending_power[device_key] = turn_on
            error_status.pop(device_key, None)
        results.refresh()

        observation = None
        try:
            async with asyncio.timeout(15):
                if turn_on:
                    await group.turn_on()
                else:
                    await group.turn_off()
        except Exception:  # noqa: BLE001 - keep group control failures visible in the UI
            logger.exception("Light group control failed for {}", group_id)
            group_errors[group_id] = (
                "Couldn’t confirm the command. Check the lights before trying again."
            )
        else:
            try:
                expected_state = "on" if turn_on else "off"
                async with asyncio.timeout(STATE_CONFIRMATION_TIMEOUT):
                    while True:
                        observation = await group.get_state()
                        confirmed = True
                        for state in observation.devices.values():
                            if state.state != expected_state:
                                confirmed = False
                                break
                        if confirmed:
                            break
                        await asyncio.sleep(STATE_POLL_INTERVAL)
            except TimeoutError:
                group_errors[group_id] = (
                    "Command sent, but not all lights have confirmed the requested state yet."
                )
            except httpx.HTTPError, ValidationError:
                group_errors[group_id] = (
                    "Command sent, but the light states couldn’t be refreshed."
                )
        finally:
            pending_groups.pop(group_id, None)
            for device_key in device_keys:
                pending_power.pop(device_key, None)

            # Show observed states, including mixed results after a timeout.
            if observation is not None:
                states_by_key = {}
                for device_id, state in observation.devices.items():
                    states_by_key[f"lights:{group_id}.devices.{device_id}"] = state
                for entry in inventory:
                    state = states_by_key.get(entry["id"])
                    if state is not None:
                        entry["state"] = state.state
                        entry.pop("error", None)
            results.refresh()

    with ui.dialog() as editor, ui.card().classes("light-editor"):
        with ui.row().classes("w-full justify-between items-center"):
            heading = ui.label().classes("text-xl").mark("light-settings-title")
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

    def toggle_group_details(group_id: str):
        expanded_groups[group_id] = not expanded_groups.get(group_id, False)
        results.refresh()

    def device_card(device: dict):
        if device["type"] != "light":
            with ui.element("div").classes("device-tile"):
                ui.icon("speaker" if device["type"] == "speaker" else "tv", size="24px")
                with ui.column().classes("tile-copy"):
                    ui.label(device["name"]).classes("tile-title")
                    ui.label(device["state"].replace("_", " ")).classes("tile-state")
            return

        device_key = device["id"]
        busy = device_key in pending_power
        is_on = pending_power.get(device_key, device["state"] == "on")
        state_text = device["state"]
        if busy:
            state_text = "Turning on…" if is_on else "Turning off…"

        with ui.element("div").classes("light-tile is-on" if is_on else "light-tile"):
            with ui.row().classes("tile-main-row"):
                # The settings button is a sibling, so it cannot trigger power.
                with (
                    ui.button(
                        on_click=partial(set_light_power, device_key, not is_on),
                        color=None,
                    )
                    .props("flat no-caps")
                    .classes("tile-action")
                    .mark(f"power-{device_key}") as power,
                    ui.row().classes("tile-content"),
                ):
                    ui.icon("lightbulb" if is_on else "lightbulb_outline", size="24px")
                    with ui.column().classes("tile-copy"):
                        ui.label(device["name"]).classes("tile-title")
                        ui.label(state_text).classes("tile-state").mark(
                            f"device-state-{device_key}"
                        )
                power.props["aria-label"] = (
                    f"Turn {'off' if is_on else 'on'} {device['name']}"
                )
                power.props["aria-pressed"] = str(is_on).lower()
                power.props["aria-busy"] = str(busy).lower()
                if busy:
                    power.disable()
                settings_button = (
                    ui.button(
                        icon="settings",
                        on_click=partial(open_settings, device_key),
                        color=None,
                    )
                    .props("flat round")
                    .classes("tile-accessory")
                    .tooltip(f"{device['name']} settings")
                    .mark(f"settings-{device_key}")
                )
                settings_button.props["aria-label"] = f"{device['name']} settings"

            message = error_status.get(device_key) or device.get("error")
            if message:
                ui.label(message).classes("error tile-error").props("role=alert").mark(
                    f"light-error-{device_key}"
                )

    def light_group_card(group, members: list[dict]):
        on_count = 0
        unknown_count = 0
        for device in members:
            if device["state"] == "on":
                on_count += 1
            elif device["state"] != "off":
                unknown_count += 1
        summary = f"{on_count} of {len(members)} lights on"
        if unknown_count:
            summary += f" · {unknown_count} unknown or unavailable"
        busy = group.group_id in pending_groups
        for device in members:
            if device["id"] in pending_power:
                busy = True

        expanded = expanded_groups.get(group.group_id, False)
        is_on = pending_groups.get(group.group_id, on_count > 0)
        state_text = summary
        if group.group_id in pending_groups:
            state_text = "Turning on…" if is_on else "Turning off…"

        with (
            ui.element("div")
            .classes("light-group")
            .mark(f"light-group-{group.group_id}")
        ):
            with ui.element("div").classes(
                "light-tile is-on" if is_on else "light-tile"
            ):
                with ui.row().classes("tile-main-row"):
                    with (
                        ui.button(
                            on_click=partial(
                                set_light_group_power,
                                group.group_id,
                                not is_on,
                            ),
                            color=None,
                        )
                        .props("flat no-caps")
                        .classes("tile-action")
                        .mark(f"group-power-{group.group_id}") as power,
                        ui.row().classes("tile-content"),
                    ):
                        ui.icon(
                            "lightbulb" if is_on else "lightbulb_outline",
                            size="24px",
                        )
                        with ui.column().classes("tile-copy"):
                            ui.label(group.display_name).classes("tile-title")
                            ui.label(state_text).classes("tile-state").mark(
                                f"group-state-{group.group_id}"
                            )
                    power.props["aria-label"] = (
                        f"Turn {'off' if is_on else 'on'} {group.display_name}"
                    )
                    power.props["aria-pressed"] = str(is_on).lower()
                    power.props["aria-busy"] = str(busy).lower()
                    if busy:
                        power.disable()

                    expand_button = (
                        ui.button(
                            icon="expand_less" if expanded else "expand_more",
                            on_click=partial(toggle_group_details, group.group_id),
                            color=None,
                        )
                        .props("flat round")
                        .classes("tile-accessory group-expand")
                        .mark(f"group-expand-{group.group_id}")
                    )
                    expand_button.props["aria-label"] = (
                        f"{'Hide' if expanded else 'Show'} individual lights in {group.display_name}"
                    )
                    expand_button.props["aria-expanded"] = str(expanded).lower()

                if group.group_id in group_errors:
                    ui.label(group_errors[group.group_id]).classes(
                        "error tile-error"
                    ).props("role=alert").mark(f"group-error-{group.group_id}")

            if expanded:
                with ui.element("div").classes("group-members"):
                    for device in sorted(
                        members,
                        key=lambda device: device["name"].casefold(),
                    ):
                        device_card(device)

    @ui.refreshable
    def results():
        query = search.value.strip().casefold()
        inventory_by_key = {}
        for device in inventory:
            inventory_by_key[device["id"]] = device

        rooms = []
        assigned_keys = set()
        groups = sorted(
            api.state.home.light_groups.values(),
            key=lambda group: group.display_name.casefold(),
        )
        for group in groups:
            room_name = group.display_name.removesuffix(" Lights")
            room_matches = (
                query in room_name.casefold() or query in group.group_id.casefold()
            )
            group_matches = room_matches or query in group.display_name.casefold()
            members = []

            # Light membership comes from the configured group objects.
            for device_id in group.devices:
                device_key = f"lights:{group.group_id}.devices.{device_id}"
                assigned_keys.add(device_key)
                device = inventory_by_key.get(device_key)
                if device is None:
                    continue
                members.append(device)
                if query in f"{device['name']} {device_key}".casefold():
                    group_matches = True

            # Speaker/TV config IDs identify their room when they match a group ID.
            room_devices = []
            for device in inventory:
                if device["type"] not in ("speaker", "tv"):
                    continue
                device_id = device["id"].partition(":")[2]
                if device_id != group.group_id:
                    continue
                assigned_keys.add(device["id"])
                if (
                    room_matches
                    or query in f"{device['name']} {device['id']}".casefold()
                ):
                    room_devices.append(device)

            visible_members = members if group_matches else []
            if visible_members or room_devices:
                rooms.append(
                    (group.group_id, room_name, group, visible_members, room_devices)
                )

        other_devices = []
        for device in inventory:
            if device["id"] in assigned_keys:
                continue
            if query in f"{device['name']} {device['id']}".casefold():
                other_devices.append(device)

        if not rooms and not other_devices:
            ui.label("No matching devices.").classes("muted py-8")
            return

        for room_id, room_name, group, members, room_devices in rooms:
            with ui.element("section").classes("w-full mb-5").mark(f"room-{room_id}"):
                ui.label(room_name).classes("text-lg mt-4 mb-3").props(
                    "role=heading aria-level=2"
                )
                with ui.element("div").classes("light-group-grid"):
                    if members:
                        light_group_card(group, members)
                    for device in sorted(
                        room_devices, key=lambda device: device["name"].casefold()
                    ):
                        device_card(device)

        if other_devices:
            with ui.element("section").classes("w-full mb-5").mark("room-other"):
                ui.label("Other devices").classes("text-lg mt-4 mb-3").props(
                    "role=heading aria-level=2"
                )
                with ui.element("div").classes("device-grid"):
                    for device in sorted(
                        other_devices, key=lambda device: device["name"].casefold()
                    ):
                        device_card(device)

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
    with ui.row().classes("w-full items-center my-4"):
        search = (
            ui.input(placeholder="Search devices…", on_change=lambda: results.refresh())
            .props("outlined dense aria-label='Search devices'")
            .classes("device-search")
        )
    loading = ui.label().classes("muted text-xs").props("role=status")
    results()
    return refresh
