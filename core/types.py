from typing import TypeAlias, Union, Tuple, Dict, Any, Literal

from discord import Embed, File

__all__ = ('OUTPUT_TYPE', 'POSSIBLE_RTFM_SOURCES')


OUTPUT_TYPE: TypeAlias = Union[Tuple[Union[Embed, str, File, Dict[str, Any], bool, None], ...], Union[Embed, str, File, Dict[str, Any], bool, None]]

POSSIBLE_RTFM_SOURCES: TypeAlias = Literal['python', 'asyncpg', 'rust', 'discordpy', 'discordpy_master', 'crates']
