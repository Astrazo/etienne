from collections.abc import Callable
from typing import Protocol


class ToolProvider(Protocol):
    def get_tools(self) -> list[Callable]: ...
