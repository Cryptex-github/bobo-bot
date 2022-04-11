from typing import TypeAlias, Any, Literal

from discord import Embed, File
from discord.ui import View

from core.constants import Constant

__all__ = ('OutputType', 'PossibleRTFMSources')


OutputType: TypeAlias = (
    tuple[Embed | str | File | dict[str, Any] | bool | Constant | View | None, ...]
    | Embed
    | str
    | File
    | dict[str, Any]
    | bool
    | Constant
    | View
    | None
)

PossibleRTFMSources: TypeAlias = Literal[
    'python', 'asyncpg', 'rust', 'discordpy', 'discordpy_master', 'crates'
]
