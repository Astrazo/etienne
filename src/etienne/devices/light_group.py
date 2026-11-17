"""A named group referencing individually registered lights."""

from .light import Light


class LightGroup:
    def __init__(
        self,
        group_id: str,
        devices: dict[str, Light],
        display_name: str | None = None,
    ):
        self.group_id = group_id
        self.display_name = display_name or group_id.replace("_", " ").title()
        self.devices = devices
