"""Attach NiceGUI to the existing FastAPI server."""

import os
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from nicegui import app as nicegui_app, ui

from .chat import build_chat
from .devices import build_devices
from .schedule import build_schedule
from .settings import build_settings
from .state import import_browser_data

ASSETS = Path(__file__).parent


def configure_theme():
    ui.colors(primary="#c5ed85", dark="#1b1d1b", dark_page="#141514")
    ui.add_css((ASSETS / "styles.css").read_text(encoding="utf-8"))


def storage_secret() -> str:
    """Keep session cookies valid across restarts without requiring extra setup."""
    if configured := os.getenv("ETIENNE_UI_SECRET"):
        return configured
    path = Path("data/ui-session.key")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        secret = secrets.token_urlsafe(48)
        path.write_text(secret, encoding="utf-8")
        return secret


def register_web(api: FastAPI) -> None:
    # Serve only public assets, never the Python modules in this directory.
    @api.get("/ui/logo.png", include_in_schema=False)
    async def logo():
        return FileResponse(ASSETS / "logo.png")

    @ui.page("/", title="Etienne")
    @ui.page("/login", title="Etienne")
    async def welcome():
        configure_theme()
        await ui.context.client.connected()
        storage = nicegui_app.storage.user
        await import_browser_data(storage)
        with ui.column().classes("login"):
            ui.image("/ui/logo.png").classes("login-logo").props(
                "fit=contain no-spinner alt=Etienne"
            )
            ui.label("Welcome home.").classes("page-title text-center w-full")
            name = (
                ui.input(
                    "Your name (optional)",
                    value=storage.get("display_name", ""),
                    placeholder="What should I call you?",
                )
                .props("outlined maxlength=40 autocomplete=nickname")
                .classes("w-full")
            )

            def enter():
                storage["display_name"] = (name.value or "").strip()[:40]
                ui.navigate.to("/index")

            name.on("keydown.enter", enter)
            ui.button("Come on in", on_click=enter).props(
                "unelevated no-caps text-color=black"
            ).classes("w-full")
            ui.label("No sign-in required yet.").classes("muted text-xs self-center")

    @ui.page("/index", title="Etienne")
    async def workspace():
        configure_theme()
        await ui.context.client.connected()
        storage = nicegui_app.storage.user
        requested_tab = await import_browser_data(storage)
        preferences = dict(storage["navigation"])
        preferences["settings"] = True
        storage["navigation"] = preferences
        if requested_tab not in preferences or not preferences[requested_tab]:
            requested_tab = next(key for key, visible in preferences.items() if visible)
        with ui.row().classes("shell"):
            with ui.column().classes("sidebar"):
                with ui.link(target="/index").classes("brand"):
                    ui.image("/ui/logo.png").props("fit=contain no-spinner alt=Etienne")
                with (
                    ui.tabs(value=requested_tab)
                    .props(
                        "vertical inline-label no-caps active-color=primary indicator-color=transparent"
                    )
                    .classes("navigation") as navigation
                ):
                    tabs = {
                        "chat": ui.tab(
                            "chat", label="Chat", icon="chat_bubble_outline"
                        ),
                        "devices": ui.tab("devices", label="Devices", icon="devices"),
                        "schedule": ui.tab("schedule", label="TV Schedule", icon="tv"),
                        "settings": ui.tab("settings", label="Settings", icon="tune"),
                    }
                    for key, tab in tabs.items():
                        tab.bind_visibility_from(storage, ("navigation", key))
                ui.button(
                    storage.get("display_name") or "You",
                    icon="logout",
                    on_click=lambda: ui.navigate.to("/login"),
                ).props("flat no-caps").classes("profile")
            with ui.tab_panels(navigation, animated=False).classes("pages"):
                with ui.tab_panel("chat"):
                    build_chat(api)
                with ui.tab_panel("devices"):
                    refresh_devices = build_devices(api)
                with ui.tab_panel("schedule"):
                    tv_names = [
                        name.replace("_", " ").title() for name in api.state.home.tvs
                    ]
                    build_schedule(storage, tv_names)
                with ui.tab_panel("settings"):
                    build_settings(storage, tabs, navigation)

        def tab_changed(event):
            if event.value == "devices":
                refresh_devices()

        navigation.on_value_change(tab_changed)
        if navigation.value == "devices":
            refresh_devices()

    ui.run_with(
        api,
        title="Etienne",
        favicon=ASSETS / "logo.png",
        dark=True,
        storage_secret=storage_secret(),
        show_welcome_message=False,
    )
