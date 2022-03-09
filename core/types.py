from typing import Union, Tuple, Dict, Any

from discord import Embed, File

__all__ = ('OUTPUT_TYPE',)


OUTPUT_TYPE = Union[Tuple[Union[Embed, str, File, Dict[str, Any], bool]], Union[Embed, str, File, Dict[str, Any], bool]]
