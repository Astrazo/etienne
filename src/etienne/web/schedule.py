"""A daily timeline built from NiceGUI buttons, labels, and a shared editor."""

from collections.abc import MutableMapping
from functools import partial

from nicegui import ui
from pydantic import ValidationError

from .state import Programme, programmes, save_programme


def minutes(time: str) -> int:
    hours, minute = map(int, time.split(":"))
    return hours * 60 + minute


def build_schedule(storage: MutableMapping, tv_names: list[str]) -> None:
    editing_id = None

    def open_editor(entry: Programme | None = None):
        nonlocal editing_id
        editing_id = entry.id if entry else None
        heading.text = "Edit programme" if entry else "Add programme"
        error.text = ""
        for field, widget in fields.items():
            widget.value = getattr(entry, field) if entry else ""
        fields["tv"].set_autocomplete(
            sorted(set(tv_names + [item.tv for item in programmes(storage)]))
        )
        editor.open()

    def save():
        values = {key: widget.value or "" for key, widget in fields.items()}
        if editing_id:
            values["id"] = editing_id
        try:
            save_programme(storage, Programme.model_validate(values))
        except ValidationError as exception:
            issue = exception.errors()[0]
            field = ".".join(str(part) for part in issue["loc"])
            error.text = f"{field.title() + ': ' if field else ''}{issue['msg'].removeprefix('Value error, ')}"
            return
        except ValueError as exception:
            error.text = str(exception)
            return
        editor.close()
        timeline.refresh()
        ui.notify("Programme saved.")

    def remove(entry: Programme):
        storage["schedule"] = [
            item.model_dump() for item in programmes(storage) if item.id != entry.id
        ]
        timeline.refresh()
        ui.notify("Programme removed.")

    with ui.dialog() as editor, ui.card().classes("programme-editor"):
        with ui.row().classes("w-full justify-between items-center"):
            heading = ui.label("Add programme").classes("text-xl")
            ui.button(icon="close", on_click=editor.close).props(
                "flat round aria-label=Close"
            )
        fields = {
            "title": ui.input("What’s on?")
            .props("outlined maxlength=100")
            .classes("w-full"),
            "tv": ui.input("Television", autocomplete=tv_names)
            .props("outlined maxlength=80")
            .classes("w-full"),
            "service": ui.input("App or channel")
            .props("outlined maxlength=80")
            .classes("w-full"),
        }
        with ui.row().classes("w-full no-wrap"):
            fields["start"] = (
                ui.input("Start time")
                .props("outlined type=time")
                .classes("flex-1 min-w-0")
            )
            fields["end"] = (
                ui.input("End time")
                .props("outlined type=time")
                .classes("flex-1 min-w-0")
            )
        error = ui.label().classes("error").props("role=alert")
        ui.button("Save programme", on_click=save).props(
            "unelevated no-caps text-color=black"
        ).classes("w-full")

    with ui.row().classes("page-heading"):
        with ui.column().classes("gap-1"):
            ui.label("TV Schedule").classes("page-title")
            ui.label("What’s on, and when.").classes("muted")
        ui.button("Add programme", icon="add", on_click=lambda: open_editor()).props(
            "unelevated no-caps text-color=black"
        )
    ui.label(
        "Daily plan for this browser session. Automatic playback isn’t connected yet."
    ).classes("notice")

    @ui.refreshable
    def timeline():
        entries = sorted(programmes(storage), key=lambda item: item.start)
        if not entries:
            with ui.column().classes("empty"):
                ui.label("Nothing planned yet.").classes("text-lg")
                ui.label("Add a programme to start your daily schedule.").classes(
                    "muted"
                )
                ui.button(
                    "Add your first programme", on_click=lambda: open_editor()
                ).props("outline no-caps")
            return
        with ui.row().classes("w-full justify-between my-5"):
            ui.label("Daily plan")
            ui.label(f"24-hour timeline · {len(entries)} programmes").classes(
                "muted text-xs"
            )
        with ui.element("div").classes("schedule-scroll"):
            with ui.element("div").classes("timeline"):
                with ui.row().classes("time-ruler"):
                    for hour in range(0, 24, 2):
                        ui.label(f"{hour:02}:00").classes("flex-1")
                for tv in sorted({entry.tv for entry in entries}):
                    with ui.row().classes("timeline-row"):
                        ui.label(tv).classes("tv-label")
                        with ui.element("div").classes("track"):
                            with (
                                ui.row().classes("time-grid").props("aria-hidden=true")
                            ):
                                for _ in range(12):
                                    ui.element("span").classes("flex-1")
                            for entry in entries:
                                if entry.tv != tv:
                                    continue
                                left = minutes(entry.start) / 14.4
                                width = (
                                    minutes(entry.end) - minutes(entry.start)
                                ) / 14.4
                                with (
                                    ui.button(
                                        color=None, on_click=partial(open_editor, entry)
                                    )
                                    .props("no-caps unelevated")
                                    .classes("programme")
                                    .style(f"left: {left}%; width: {width}%")
                                ):
                                    with ui.column().classes("programme-label"):
                                        ui.label(
                                            f"{entry.start} – {entry.end}"
                                        ).classes("text-xs")
                                        ui.label(entry.title).classes("font-medium")
                                        ui.label(entry.service).classes("text-xs")
        for entry in entries:
            with ui.row().classes("programme-entry"):
                ui.icon("tv").classes("muted")
                with ui.column().classes("flex-1 min-w-0 gap-1"):
                    ui.label(entry.title)
                    ui.label(
                        f"{entry.start} – {entry.end} · {entry.tv} · {entry.service}"
                    ).classes("muted text-xs")
                ui.button("Edit", on_click=partial(open_editor, entry)).props(
                    "outline no-caps"
                )
                ui.button(icon="close", on_click=partial(remove, entry)).props(
                    "flat round aria-label='Delete programme'"
                ).mark("delete-programme")

    timeline()
