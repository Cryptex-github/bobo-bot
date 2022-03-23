from typing import TypeAlias, Union, Tuple, Dict, Any, Literal

from discord import Embed, File

from core.constants import Constant

__all__ = ('OUTPUT_TYPE', 'POSSIBLE_RTFM_SOURCES')


OUTPUT_TYPE: TypeAlias = Union[Tuple[Union[Embed, str, File, Dict[str, Any], bool, Constant, None], ...], Union[Embed, str, File, Dict[str, Any], bool, Constant, None]]

POSSIBLE_RTFM_SOURCES: TypeAlias = Literal['python', 'asyncpg', 'rust', 'discordpy', 'discordpy_master', 'crates']
