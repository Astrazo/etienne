"""Daily plans and the one-time import from the previous browser-only UI."""

from collections.abc import MutableMapping
from uuid import uuid4

from nicegui import ui
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class Programme(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=100)
    tv: str = Field(min_length=1, max_length=80)
    service: str = Field(min_length=1, max_length=80)
    start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def check_times(self):
        if self.end <= self.start:
            raise ValueError(
                "End time must follow start time. Split overnight programmes into two entries."
            )
        return self


def programmes(storage: MutableMapping) -> list[Programme]:
    return [Programme.model_validate(entry) for entry in storage.get("schedule", [])]


def save_programme(storage: MutableMapping, entry: Programme) -> None:
    remaining = [other for other in programmes(storage) if other.id != entry.id]
    for other in remaining:
        if (
            other.tv.casefold() == entry.tv.casefold()
            and entry.start < other.end
            and entry.end > other.start
        ):
            raise ValueError(
                "This television already has a programme in that time slot."
            )
    storage["schedule"] = [other.model_dump() for other in [*remaining, entry]]


async def import_browser_data(storage: MutableMapping) -> str:
    """Read legacy localStorage once; all new interactions use NiceGUI's Python API.

    Keep the original browser data intact. The fragment read also preserves old
    /index#devices-style bookmarks when opening the new interface.
    """
    legacy = await ui.run_javascript("""
        const result = {tab: location.hash.slice(1)};
        for (const key of ['etienne.navigation', 'etienne.schedule', 'etienne.displayName']) {
            try { result[key] = JSON.parse(localStorage.getItem(key)); }
            catch { result[key] = null; }
        }
        return result;
    """)
    if not storage.get("legacy_imported"):
        navigation = legacy.get("etienne.navigation")
        if isinstance(navigation, dict):
            storage.setdefault(
                "navigation",
                {
                    key: navigation.get(key) is not False
                    for key in ("chat", "devices", "schedule", "settings")
                },
            )
        name = legacy.get("etienne.displayName")
        if isinstance(name, str):
            storage.setdefault("display_name", name[:40])
        entries = legacy.get("etienne.schedule")
        if isinstance(entries, list) and "schedule" not in storage:
            imported = {}
            for item in entries:
                try:
                    entry = Programme.model_validate(item)
                    save_programme(imported, entry)
                except ValidationError, ValueError:
                    ui.notify(
                        "An invalid old TV entry couldn’t be imported. The original is still in browser storage.",
                        type="warning",
                    )
            storage["schedule"] = imported.get("schedule", [])
        storage["legacy_imported"] = True
    storage.setdefault(
        "navigation", {key: True for key in ("chat", "devices", "schedule", "settings")}
    )
    storage.setdefault("schedule", [])
    return legacy.get("tab", "chat")
