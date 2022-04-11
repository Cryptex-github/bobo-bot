from typing import TypeAlias, Tuple, Dict, Any, Literal

from discord import Embed, File
from discord.ui import View

from core.constants import Constant

__all__ = ('OUTPUT_TYPE', 'POSSIBLE_RTFM_SOURCES')


OUTPUT_TYPE: TypeAlias = (
    Tuple[Embed | str | File | Dict[str, Any] | bool | Constant | View | None, ...]
    | Embed
    | str
    | File
    | Dict[str, Any]
    | bool
    | Constant
    | View
    | None
)

POSSIBLE_RTFM_SOURCES: TypeAlias = Literal[
    'python', 'asyncpg', 'rust', 'discordpy', 'discordpy_master', 'crates'
]
