import re

__all__ = ('Regexs')

class Regexs:
    COG_REGEX = re.compile(r'cogs/[a-z]+\.py')
