"""Sidebar preferences stored by NiceGUI for this anonymous browser session."""

from collections.abc import MutableMapping

from nicegui import ui


def build_settings(
    storage: MutableMapping, tabs: dict[str, ui.tab], navigation: ui.tabs
) -> None:
    def change_tab(key: str, enabled: bool):
        preferences = dict(storage["navigation"])
        preferences[key] = enabled
        preferences["settings"] = True
        storage["navigation"] = preferences
        if not preferences.get(navigation.value, True):
            navigation.value = next(name for name in tabs if preferences[name])

    ui.label("Settings").classes("page-title")
    ui.label("Keep what you use.").classes("muted mb-6")
    with ui.column().classes("settings"):
        ui.label("Sidebar tabs").classes("text-lg")
        ui.label("Choose which tabs appear.").classes("muted")
        for key, tab in tabs.items():
            with ui.row().classes("setting-row"):
                switch = ui.switch(
                    tab.props["label"],
                    value=storage["navigation"].get(key, True),
                    on_change=lambda event, name=key: change_tab(name, event.value),
                )
                if key == "settings":
                    switch.value = True
                    switch.disable()
                    ui.label("Always visible so you can bring tabs back.").classes(
                        "muted text-xs"
                    )
        ui.label(
            "Preferences and plans are saved on this server for this browser’s anonymous session. They aren’t shared with other browsers."
        ).classes("notice mt-6")
        ui.label("Preview access").classes("text-lg mt-6")
        ui.label(
            "The welcome page doesn’t check credentials yet. Hiding a tab changes the display, not permissions."
        ).classes("muted")
