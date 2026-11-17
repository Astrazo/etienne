from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel


class Device(Protocol):
    def get_tools(self) -> list[Callable]: ...
    async def get_state(self) -> BaseModel: ...
