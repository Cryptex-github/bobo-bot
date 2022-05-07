from __future__ import annotations

from typing import TypeAlias, Literal

from discord import Embed, File
from discord.ui import View

from core.constants import Constant

__all__ = ('OutputType', 'PossibleRTFMSources')


JsonValue: TypeAlias = (
    str | int | float | bool | list['JsonValue'] | dict[str, 'JsonValue'] | None
)
Json: TypeAlias = dict[str, JsonValue] | list[JsonValue]

OutputType: TypeAlias = (
    tuple[Embed | str | File | Json | bool | Constant | View | None, ...]
    | Embed
    | str
    | File
    | Json
    | bool
    | Constant
    | View
    | None
)

PossibleRTFMSources: TypeAlias = Literal[
    'python', 'asyncpg', 'rust', 'discordpy', 'discordpy_master', 'crates'
]
