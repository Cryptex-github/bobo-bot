import re

__all__ = ('Regexs')

class Regexs:
    __slots__ = ('COG_REGEX',)

    COG_REGEX = re.compile(r'cogs/[a-z]+\.py')
    SPHINX_ENTRY_REGEX = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
