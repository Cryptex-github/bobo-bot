import re

__all__ = ('Regexs')

class Regexs:
    __slots__ = ('COG_REGEX',)

    COG_REGEX = re.compile(r'cogs/[a-z]+\.py')
