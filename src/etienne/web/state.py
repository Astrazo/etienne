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
        # Time strings use HH:MM, so they can be compared directly within one day.
        if self.end <= self.start:
            raise ValueError(
                "End time must follow start time. Split overnight programmes into two entries."
            )
        return self


def programmes(storage: MutableMapping) -> list[Programme]:
    # Validate saved entries before the UI uses them.
    entries = []
    for entry in storage.get("schedule", []):
        entries.append(Programme.model_validate(entry))
    return entries


def save_programme(storage: MutableMapping, entry: Programme) -> None:
    # Exclude the old version of the entry when editing an existing programme.
    remaining = []
    for other in programmes(storage):
        if other.id != entry.id:
            remaining.append(other)

    # Reject overlapping programmes on the same TV before saving anything.
    for other in remaining:
        if (
            other.tv.casefold() == entry.tv.casefold()
            and entry.start < other.end
            and entry.end > other.start
        ):
            raise ValueError(
                "This television already has a programme in that time slot."
            )
    # Store plain dictionaries for NiceGUI's persistent storage.
    saved_entries = []
    for other in remaining:
        saved_entries.append(other.model_dump())
    saved_entries.append(entry.model_dump())
    storage["schedule"] = saved_entries


async def import_browser_data(storage: MutableMapping) -> str:
    """Read legacy localStorage once; all new interactions use NiceGUI's Python API.

    Keep the original browser data intact. The fragment read also preserves old
    /index#devices-style bookmarks when opening the new interface.
    """
    # Read the old browser storage and any tab named in the URL fragment.
    legacy = await ui.run_javascript("""
        const result = {tab: location.hash.slice(1)};
        for (const key of ['etienne.navigation', 'etienne.schedule', 'etienne.displayName']) {
            try { result[key] = JSON.parse(localStorage.getItem(key)); }
            catch { result[key] = null; }
        }
        return result;
    """)

    # Import old preferences only once, without replacing newer server values.
    if not storage.get("legacy_imported"):
        navigation = legacy.get("etienne.navigation")
        if isinstance(navigation, dict):
            preferences = {}
            for key in ("chat", "devices", "schedule", "settings"):
                preferences[key] = navigation.get(key) is not False
            storage.setdefault("navigation", preferences)

        name = legacy.get("etienne.displayName")
        if isinstance(name, str):
            storage.setdefault("display_name", name[:40])

        # Validate old schedule entries individually so invalid entries can be skipped.
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

    # Supply defaults for browsers without saved preferences or a schedule.
    default_navigation = {}
    for key in ("chat", "devices", "schedule", "settings"):
        default_navigation[key] = True
    storage.setdefault("navigation", default_navigation)
    storage.setdefault("schedule", [])
    return legacy.get("tab", "chat")
